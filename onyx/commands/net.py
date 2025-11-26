"""
Network utilities command for connectivity and diagnostics.
"""

import socket
import subprocess
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import click
from tqdm import tqdm


@click.group()
def net():
    """Network connectivity and diagnostic tools."""
    pass


@net.command()
@click.argument('host')
@click.option('--count', '-c', type=int, default=4, help='Number of ping packets to send')
@click.option('--timeout', '-t', type=int, default=3, help='Timeout in seconds')
@click.option('--interval', '-i', type=float, default=1.0, help='Interval between pings in seconds')
@click.option('--size', '-s', type=int, default=32, help='Packet size in bytes')
@click.option('--continuous', is_flag=True, help='Continuous ping (Ctrl+C to stop)')
@click.option('--ipv6', '-6', is_flag=True, help='Use IPv6')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def ping(host: str, count: int, timeout: int, interval: float, size: int, 
         continuous: bool, ipv6: bool, output: str):
    """Ping a host to test connectivity."""

    if output == 'table':
        click.echo(f"🏓 Pinging {host} with {size} bytes of data...")
        if continuous:
            click.echo("Press Ctrl+C to stop continuous ping")
    
    results = []
    sent = 0
    received = 0
    lost = 0
    min_time = float('inf')
    max_time = 0
    total_time = 0
    
    try:
        ping_count = float('inf') if continuous else count
        
        while sent < ping_count:
            sent += 1
            start_time = time.time()
            
            try:
                # Perform ping
                if _ping_host(host, timeout, ipv6):
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    received += 1
                    
                    # Update statistics
                    min_time = min(min_time, response_time)
                    max_time = max(max_time, response_time)
                    total_time += response_time
                    
                    result = {
                        'sequence': sent,
                        'time': response_time,
                        'status': 'success'
                    }
                    
                    if output == 'table':
                        click.echo(f"Reply from {host}: bytes={size} time={response_time:.1f}ms")
                    
                else:
                    lost += 1
                    result = {
                        'sequence': sent,
                        'time': None,
                        'status': 'timeout'
                    }
                    
                    if output == 'table':
                        click.echo(f"Request timed out.")
                
                results.append(result)
                
                if not continuous and sent < count:
                    time.sleep(interval)
                elif continuous:
                    time.sleep(interval)
                    
            except KeyboardInterrupt:
                if continuous:
                    break
                else:
                    raise
                    
    except KeyboardInterrupt:
        click.echo("\nPing interrupted by user")
    
    # Calculate statistics
    if received > 0:
        avg_time = total_time / received
        loss_percent = (lost / sent) * 100
    else:
        avg_time = 0
        loss_percent = 100
        min_time = 0
    
    # Display summary
    if output == 'table':
        click.echo(f"\n--- {host} ping statistics ---")
        click.echo(f"Packets: Sent = {sent}, Received = {received}, Lost = {lost} ({loss_percent:.1f}% loss)")
        
        if received > 0:
            click.echo(f"Approximate round trip times in milli-seconds:")
            click.echo(f"    Minimum = {min_time:.1f}ms, Maximum = {max_time:.1f}ms, Average = {avg_time:.1f}ms")
    
    elif output == 'json':
        summary = {
            'host': host,
            'packets_sent': sent,
            'packets_received': received,
            'packets_lost': lost,
            'loss_percent': loss_percent,
            'min_time': min_time if min_time != float('inf') else 0,
            'max_time': max_time,
            'avg_time': avg_time,
            'results': results
        }
        click.echo(json.dumps(summary, indent=2))


@net.command()
@click.argument('host')
@click.option('--max-hops', '-m', type=int, default=30, help='Maximum number of hops')
@click.option('--timeout', '-t', type=int, default=5, help='Timeout per hop in seconds')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def traceroute(host: str, max_hops: int, timeout: int, output: str):
    """Trace the route to a destination host."""

    if output == 'table':
        click.echo(f"🗺️ Tracing route to {host} with maximum {max_hops} hops...")
    
    results = []
    
    try:
        for hop in range(1, max_hops + 1):
            hop_result = _traceroute_hop(host, hop, timeout)
            results.append(hop_result)
            
            if output == 'table':
                if hop_result['status'] == 'success':
                    click.echo(f"{hop:2d}  {hop_result['time']:.1f} ms  {hop_result['ip']} ({hop_result['hostname']})")
                elif hop_result['status'] == 'timeout':
                    click.echo(f"{hop:2d}  *  Request timed out")
                else:
                    click.echo(f"{hop:2d}  !  {hop_result['error']}")
            
            # Stop if we reached the destination
            if hop_result['status'] == 'success' and _resolve_hostname(host) == hop_result['ip']:
                if output == 'table':
                    click.echo(f"\nTrace complete. Destination reached in {hop} hops.")
                break
        else:
            if output == 'table':
                click.echo(f"\nTrace incomplete. Maximum hops ({max_hops}) reached.")
    
    except KeyboardInterrupt:
        click.echo("\nTraceroute interrupted by user")
    
    if output == 'json':
        summary = {
            'host': host,
            'max_hops': max_hops,
            'completed_hops': len(results),
            'results': results
        }
        click.echo(json.dumps(summary, indent=2))


@net.command()
@click.argument('host')
@click.argument('port', type=int)
@click.option('--timeout', '-t', type=int, default=5, help='Connection timeout in seconds')
@click.option('--protocol', '-p', type=click.Choice(['tcp', 'udp']), default='tcp', help='Protocol to use')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def port(host: str, port: int, timeout: int, protocol: str, output: str):
    """Check if a specific port is open on a host."""

    if output == 'table':
        click.echo(f"🔌 Checking {protocol.upper()} port {port} on {host}...")
    
    start_time = time.time()
    result = _check_port(host, port, timeout, protocol)
    end_time = time.time()
    
    response_time = (end_time - start_time) * 1000
    
    if output == 'table':
        if result['status'] == 'open':
            click.echo(f"✅ Port {port} is OPEN on {host} ({response_time:.1f}ms)")
            if result.get('service'):
                click.echo(f"   Service: {result['service']}")
        elif result['status'] == 'closed':
            click.echo(f"❌ Port {port} is CLOSED on {host}")
        elif result['status'] == 'filtered':
            click.echo(f"🚫 Port {port} is FILTERED on {host}")
        else:
            click.echo(f"⚠️ Error checking port {port}: {result.get('error', 'Unknown error')}")
    
    elif output == 'json':
        result['host'] = host
        result['port'] = port
        result['protocol'] = protocol
        result['response_time'] = response_time
        click.echo(json.dumps(result, indent=2))


@net.command()
@click.argument('host')
@click.option('--start-port', '-s', type=int, default=1, help='Start port number')
@click.option('--end-port', '-e', type=int, default=1000, help='End port number')
@click.option('--timeout', '-t', type=float, default=1.0, help='Connection timeout in seconds')
@click.option('--protocol', '-p', type=click.Choice(['tcp', 'udp']), default='tcp', help='Protocol to use')
@click.option('--threads', type=int, default=100, help='Number of concurrent threads')
@click.option('--common-ports', '-c', is_flag=True, help='Scan only common ports')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def scan(host: str, start_port: int, end_port: int, timeout: float, protocol: str,
         threads: int, common_ports: bool, output: str):
    """Scan a range of ports on a host."""
    
    if common_ports:
        ports_to_scan = _get_common_ports()
        click.echo(f"🔍 Scanning {len(ports_to_scan)} common ports on {host}...")
    else:
        ports_to_scan = list(range(start_port, end_port + 1))
        click.echo(f"🔍 Scanning ports {start_port}-{end_port} on {host}...")
    
    open_ports = []
    closed_ports = []
    filtered_ports = []
    
    def scan_port(port):
        result = _check_port(host, port, timeout, protocol)
        return port, result
    
    # Use thread pool for concurrent scanning
    with ThreadPoolExecutor(max_workers=threads) as executor:
        # Submit all port scan tasks
        future_to_port = {
            executor.submit(scan_port, port): port 
            for port in ports_to_scan
        }
        
        # Process results with progress bar
        with tqdm(total=len(ports_to_scan), desc="Scanning ports", 
                 disable=(output == 'json')) as pbar:
            
            for future in as_completed(future_to_port):
                port, result = future.result()
                
                if result['status'] == 'open':
                    open_ports.append((port, result))
                elif result['status'] == 'closed':
                    closed_ports.append(port)
                elif result['status'] == 'filtered':
                    filtered_ports.append(port)
                
                pbar.update(1)
    
    # Sort results
    open_ports.sort(key=lambda x: x[0])
    closed_ports.sort()
    filtered_ports.sort()
    
    # Display results
    if output == 'table':
        click.echo(f"\n📊 Scan results for {host}:")
        click.echo(f"   Open ports: {len(open_ports)}")
        click.echo(f"   Closed ports: {len(closed_ports)}")
        click.echo(f"   Filtered ports: {len(filtered_ports)}")
        
        if open_ports:
            click.echo(f"\n✅ Open ports:")
            for port, result in open_ports:
                service_info = f" ({result['service']})" if result.get('service') else ""
                click.echo(f"   {port}/{protocol}{service_info}")
        
        if filtered_ports:
            click.echo(f"\n🚫 Filtered ports: {', '.join(map(str, filtered_ports[:10]))}")
            if len(filtered_ports) > 10:
                click.echo(f"   ... and {len(filtered_ports) - 10} more")
    
    elif output == 'json':
        results = {
            'host': host,
            'protocol': protocol,
            'scan_range': f"{start_port}-{end_port}" if not common_ports else "common_ports",
            'open_ports': [{'port': port, **result} for port, result in open_ports],
            'closed_ports': closed_ports,
            'filtered_ports': filtered_ports,
            'summary': {
                'total_scanned': len(ports_to_scan),
                'open': len(open_ports),
                'closed': len(closed_ports),
                'filtered': len(filtered_ports)
            }
        }
        click.echo(json.dumps(results, indent=2))


@net.command()
@click.argument('hostname')
@click.option(
    '--record-type',
    '-t',
    type=click.Choice(['A', 'AAAA']),  # limited to what _dns_lookup actually supports
    default='A',
    help='DNS record type to query (currently supports A and AAAA)',
)
@click.option('--nameserver', '-n', help='Use specific nameserver (not used with socket backend yet)')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def dns(hostname: str, record_type: str, nameserver: str, output: str):
    """Perform DNS lookup for a hostname."""
    
    click.echo(f"🔍 DNS lookup for {hostname} (type: {record_type})")
    
    if nameserver:
        click.echo(f"Using nameserver: {nameserver}")
    
    try:
        results = _dns_lookup(hostname, record_type, nameserver)
        
        if output == 'table':
            if results:
                click.echo(f"\n📋 DNS records for {hostname}:")
                for record in results:
                    click.echo(f"   {record['type']:<8} {record['value']}")
                    if record.get('ttl'):
                        click.echo(f"            TTL: {record['ttl']}")
            else:
                click.echo(f"❌ No {record_type} records found for {hostname}")
        
        elif output == 'json':
            result_data = {
                'hostname': hostname,
                'record_type': record_type,
                'nameserver': nameserver,
                'records': results
            }
            click.echo(json.dumps(result_data, indent=2))
    
    except Exception as e:
        click.echo(f"❌ DNS lookup failed: {e}", err=True)


@net.command()
@click.argument('ip_or_domain')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def whois(ip_or_domain: str, output: str):
    """Get WHOIS information for an IP address or domain."""
    
    click.echo(f"🔍 WHOIS lookup for {ip_or_domain}")
    
    try:
        whois_data = _whois_lookup(ip_or_domain)
        
        if output == 'table':
            click.echo(f"\n📋 WHOIS information for {ip_or_domain}:")
            click.echo("-" * 50)
            
            for line in whois_data.split('\n'):
                line = line.strip()
                if line and not line.startswith('%') and not line.startswith('#'):
                    click.echo(f"   {line}")
        
        elif output == 'json':
            # Parse WHOIS data into structured format
            parsed_data = _parse_whois_data(whois_data)
            result = {
                'query': ip_or_domain,
                'raw_data': whois_data,
                'parsed_data': parsed_data
            }
            click.echo(json.dumps(result, indent=2))
    
    except Exception as e:
        click.echo(f"❌ WHOIS lookup failed: {e}", err=True)


def _ping_host(host: str, timeout: int, ipv6: bool = False) -> bool:
    """Ping a host and return True if successful."""
    try:
        # Resolve hostname to IP
        family = socket.AF_INET6 if ipv6 else socket.AF_INET
        ip = socket.getaddrinfo(host, None, family)[0][4][0]
        
        # Create socket
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Try to connect
        result = sock.connect_ex((ip, 80))  # Use port 80 as default
        sock.close()
        
        return result == 0
        
    except Exception:
        return False


def _traceroute_hop(host: str, hop: int, timeout: int) -> Dict:
    """Perform one hop of traceroute."""
    try:
        # Simple implementation using socket with TTL
        # In a real implementation, you might want to use raw sockets or system commands
        
        # For now, we'll simulate traceroute behavior
        # This is a simplified version and may not work on all systems
        
        import platform
        system = platform.system().lower()
        
        if system == 'windows':
            cmd = ['tracert', '-h', str(hop), '-w', str(timeout * 1000), host]
        else:
            cmd = ['traceroute', '-m', str(hop), '-w', str(timeout), host]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            # Parse the output (simplified)
            lines = result.stdout.split('\n')
            
            for line in lines:
                if f' {hop} ' in line or f'{hop:2d}' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        # Extract IP and time from traceroute output
                        time_str = None
                        ip_addr = None
                        hostname = None
                        
                        for part in parts:
                            if 'ms' in part:
                                time_str = part.replace('ms', '')
                            elif '.' in part and part.replace('.', '').replace(':', '').isdigit():
                                ip_addr = part
                        
                        if time_str and ip_addr:
                            try:
                                hostname = socket.gethostbyaddr(ip_addr)[0]
                            except:
                                hostname = ip_addr
                            
                            return {
                                'hop': hop,
                                'ip': ip_addr,
                                'hostname': hostname,
                                'time': float(time_str),
                                'status': 'success'
                            }
            
            return {
                'hop': hop,
                'status': 'timeout'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'hop': hop,
                'status': 'timeout'
            }
        except Exception as e:
            return {
                'hop': hop,
                'status': 'error',
                'error': str(e)
            }
    
    except Exception as e:
        return {
            'hop': hop,
            'status': 'error',
            'error': str(e)
        }


def _check_port(host: str, port: int, timeout: float, protocol: str) -> Dict:
    """Check if a port is open on a host."""
    try:
        if protocol == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                service = _get_service_name(port, protocol)
                return {
                    'status': 'open',
                    'service': service
                }
            else:
                return {'status': 'closed'}
        
        elif protocol == 'udp':
            # UDP is more complex to check reliably
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            
            try:
                sock.sendto(b'', (host, port))
                sock.recv(1024)
                return {'status': 'open'}
            except socket.timeout:
                return {'status': 'open'}  # UDP timeout often means the port is open
            except ConnectionRefusedError:
                return {'status': 'closed'}
            except Exception:
                return {'status': 'filtered'}
            finally:
                sock.close()
    
    except socket.gaierror:
        return {'status': 'error', 'error': 'Host not found'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def _get_common_ports() -> List[int]:
    """Return list of commonly used ports."""
    return [
        21,    # FTP
        22,    # SSH
        23,    # Telnet
        25,    # SMTP
        53,    # DNS
        80,    # HTTP
        110,   # POP3
        111,   # RPC
        135,   # Microsoft RPC
        139,   # NetBIOS
        143,   # IMAP
        443,   # HTTPS
        993,   # IMAPS
        995,   # POP3S
        1723,  # PPTP
        3306,  # MySQL
        3389,  # RDP
        5432,  # PostgreSQL
        5900,  # VNC
        6379,  # Redis
        8080,  # HTTP Alt
        8443,  # HTTPS Alt
        9200,  # Elasticsearch
        27017, # MongoDB
    ]


def _get_service_name(port: int, protocol: str) -> Optional[str]:
    """Get service name for a port."""
    try:
        return socket.getservbyport(port, protocol)
    except OSError:
        # Common services not in the system database
        common_services = {
            21: 'ftp',
            22: 'ssh',
            23: 'telnet',
            25: 'smtp',
            53: 'dns',
            80: 'http',
            110: 'pop3',
            143: 'imap',
            443: 'https',
            993: 'imaps',
            995: 'pop3s',
            3306: 'mysql',
            3389: 'rdp',
            5432: 'postgresql',
            5900: 'vnc',
            6379: 'redis',
            8080: 'http-alt',
            8443: 'https-alt',
            9200: 'elasticsearch',
            27017: 'mongodb',
        }
        return common_services.get(port)


def _resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP address."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def _dns_lookup(hostname: str, record_type: str, nameserver: Optional[str] = None) -> List[Dict]:
    """Perform DNS lookup."""
    results = []

    try:
        if record_type == 'A':
            try:
                ips = socket.gethostbyname_ex(hostname)[2]
                for ip in ips:
                    results.append({
                        'type': 'A',
                        'value': ip,
                    })
            except socket.gaierror:
                pass

        elif record_type == 'AAAA':
            try:
                ipv6_info = socket.getaddrinfo(hostname, None, socket.AF_INET6)
                for info in ipv6_info:
                    results.append({
                        'type': 'AAAA',
                        'value': info[4][0],
                    })
            except socket.gaierror:
                pass

    except Exception as e:
        raise Exception(f"DNS lookup failed: {e}")

    return results


def _whois_lookup(query: str) -> str:
    """Perform WHOIS lookup."""
    try:
        import platform
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows doesn't have built-in whois, we could use nslookup
            result = subprocess.run(
                ['nslookup', query],
                capture_output=True,
                text=True,
                timeout=30
            )
        else:
            # Unix-like systems
            result = subprocess.run(
                ['whois', query],
                capture_output=True,
                text=True,
                timeout=30
            )
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"WHOIS lookup failed: {result.stderr}"
    
    except subprocess.TimeoutExpired:
        return "WHOIS lookup timed out"
    except FileNotFoundError:
        return "WHOIS command not available on this system"
    except Exception as e:
        return f"WHOIS lookup failed: {e}"


def _parse_whois_data(whois_data: str) -> Dict:
    """Parse WHOIS data into structured format."""
    parsed = {}
    
    for line in whois_data.split('\n'):
        line = line.strip()
        
        if ':' in line and not line.startswith('%') and not line.startswith('#'):
            key, value = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_')
            value = value.strip()
            
            if key and value:
                if key in parsed:
                    if isinstance(parsed[key], list):
                        parsed[key].append(value)
                    else:
                        parsed[key] = [parsed[key], value]
                else:
                    parsed[key] = value
    
    return parsed
