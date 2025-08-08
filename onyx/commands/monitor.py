"""
System monitoring command for resource tracking.
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque
import click
import psutil
from tqdm import tqdm


@click.group()
def monitor():
    """System resource monitoring and process management."""
    pass


@monitor.command()
@click.option('--interval', '-i', type=float, default=1.0, help='Update interval in seconds')
@click.option('--duration', '-d', type=int, help='Duration to monitor in seconds')
@click.option('--output', '-o', type=click.Choice(['live', 'json', 'csv']), default='live', help='Output format')
@click.option('--save', '-s', type=click.Path(), help='Save output to file')
@click.option('--alert-cpu', type=float, default=90.0, help='CPU usage alert threshold (%)')
@click.option('--alert-memory', type=float, default=90.0, help='Memory usage alert threshold (%)')
@click.option('--alert-disk', type=float, default=90.0, help='Disk usage alert threshold (%)')
def system(interval: float, duration: int, output: str, save: str, 
          alert_cpu: float, alert_memory: float, alert_disk: float):
    """Monitor overall system resources."""
    
    click.echo("🖥️ System Resource Monitor")
    click.echo(f"⏱️ Update interval: {interval}s")
    
    if duration:
        click.echo(f"⏰ Duration: {duration}s")
    else:
        click.echo("⏰ Duration: Continuous (Ctrl+C to stop)")
    
    click.echo(f"🚨 Alerts: CPU>{alert_cpu}%, Memory>{alert_memory}%, Disk>{alert_disk}%")
    click.echo()
    
    data_points = []
    start_time = time.time()
    alerts = []
    
    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if duration and elapsed >= duration:
                break
            
            # Collect system metrics
            metrics = _collect_system_metrics()
            metrics['timestamp'] = datetime.now().isoformat()
            metrics['elapsed'] = elapsed
            
            data_points.append(metrics)
            
            # Check for alerts
            current_alerts = _check_alerts(metrics, alert_cpu, alert_memory, alert_disk)
            alerts.extend(current_alerts)
            
            # Display live output
            if output == 'live':
                _display_live_system_metrics(metrics, current_alerts)
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        click.echo("\n🛑 Monitoring stopped by user")
    
    # Save data if requested
    if save:
        _save_monitoring_data(data_points, save, output)
        click.echo(f"💾 Data saved to: {save}")
    
    # Display summary
    if data_points:
        _display_system_summary(data_points, alerts)


@monitor.command()
@click.option('--top', '-t', type=int, default=10, help='Number of top processes to show')
@click.option('--sort-by', type=click.Choice(['cpu', 'memory', 'pid', 'name']), default='cpu', help='Sort criteria')
@click.option('--filter-user', '-u', help='Filter by username')
@click.option('--filter-name', '-n', help='Filter by process name pattern')
@click.option('--interval', '-i', type=float, default=2.0, help='Update interval in seconds')
@click.option('--output', '-o', type=click.Choice(['live', 'json']), default='live', help='Output format')
@click.option('--show-threads', is_flag=True, help='Show thread count')
@click.option('--show-connections', is_flag=True, help='Show network connections')
def processes(top: int, sort_by: str, filter_user: str, filter_name: str, 
             interval: float, output: str, show_threads: bool, show_connections: bool):
    """Monitor running processes."""
    
    click.echo("📊 Process Monitor")
    click.echo(f"🔝 Top {top} processes sorted by {sort_by}")
    
    if filter_user:
        click.echo(f"👤 User filter: {filter_user}")
    if filter_name:
        click.echo(f"🔍 Name filter: {filter_name}")
    
    click.echo()
    
    try:
        while True:
            processes_data = _collect_process_metrics(
                top, sort_by, filter_user, filter_name, 
                show_threads, show_connections
            )
            
            if output == 'live':
                _display_live_processes(processes_data, show_threads, show_connections)
            elif output == 'json':
                click.echo(json.dumps(processes_data, indent=2, default=str))
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        click.echo("\n🛑 Process monitoring stopped")


@monitor.command()
@click.option('--interval', '-i', type=float, default=1.0, help='Update interval in seconds')
@click.option('--interface', help='Monitor specific network interface')
@click.option('--duration', '-d', type=int, help='Duration to monitor in seconds')
@click.option('--output', '-o', type=click.Choice(['live', 'json']), default='live', help='Output format')
def network(interval: float, interface: str, duration: int, output: str):
    """Monitor network activity."""
    
    click.echo("🌐 Network Activity Monitor")
    
    if interface:
        click.echo(f"🔗 Interface: {interface}")
    else:
        click.echo("🔗 All interfaces")
    
    click.echo()
    
    previous_stats = None
    data_points = []
    start_time = time.time()
    
    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if duration and elapsed >= duration:
                break
            
            # Collect network metrics
            current_stats = _collect_network_metrics(interface)
            
            if previous_stats:
                # Calculate rates
                time_delta = interval
                rates = _calculate_network_rates(previous_stats, current_stats, time_delta)
                rates['timestamp'] = datetime.now().isoformat()
                rates['elapsed'] = elapsed
                
                data_points.append(rates)
                
                if output == 'live':
                    _display_live_network_metrics(rates)
                elif output == 'json':
                    click.echo(json.dumps(rates, indent=2, default=str))
            
            previous_stats = current_stats
            time.sleep(interval)
    
    except KeyboardInterrupt:
        click.echo("\n🛑 Network monitoring stopped")
    
    # Display summary
    if data_points:
        _display_network_summary(data_points)


@monitor.command()
@click.option('--path', '-p', multiple=True, help='Monitor specific paths (can specify multiple)')
@click.option('--interval', '-i', type=float, default=2.0, help='Update interval in seconds')
@click.option('--output', '-o', type=click.Choice(['live', 'json']), default='live', help='Output format')
@click.option('--show-inodes', is_flag=True, help='Show inode information')
def disk(path: tuple, interval: float, output: str, show_inodes: bool):
    """Monitor disk usage and I/O."""
    
    click.echo("💾 Disk Monitor")
    
    if path:
        click.echo(f"📁 Monitoring paths: {', '.join(path)}")
    else:
        click.echo("📁 Monitoring all mounted filesystems")
    
    click.echo()
    
    previous_io_stats = None
    
    try:
        while True:
            # Collect disk metrics
            disk_usage = _collect_disk_usage(path, show_inodes)
            current_io_stats = _collect_disk_io()
            
            disk_metrics = {
                'usage': disk_usage,
                'timestamp': datetime.now().isoformat()
            }
            
            # Calculate I/O rates if we have previous data
            if previous_io_stats:
                io_rates = _calculate_disk_io_rates(previous_io_stats, current_io_stats, interval)
                disk_metrics['io_rates'] = io_rates
            
            if output == 'live':
                _display_live_disk_metrics(disk_metrics, show_inodes)
            elif output == 'json':
                click.echo(json.dumps(disk_metrics, indent=2, default=str))
            
            previous_io_stats = current_io_stats
            time.sleep(interval)
    
    except KeyboardInterrupt:
        click.echo("\n🛑 Disk monitoring stopped")


@monitor.command()
@click.option('--duration', '-d', type=int, default=60, help='Duration to monitor in seconds')
@click.option('--interval', '-i', type=float, default=1.0, help='Update interval in seconds')
@click.option('--output', '-o', type=click.Choice(['summary', 'json']), default='summary', help='Output format')
def performance(duration: int, interval: float, output: str):
    """Run comprehensive performance benchmark."""
    
    click.echo("🏃 Performance Benchmark")
    click.echo(f"⏰ Duration: {duration} seconds")
    click.echo(f"⏱️ Interval: {interval} seconds")
    click.echo()
    
    benchmark_data = {
        'start_time': datetime.now().isoformat(),
        'duration': duration,
        'interval': interval,
        'samples': []
    }
    
    try:
        with tqdm(total=duration, desc="Benchmarking", unit="s") as pbar:
            start_time = time.time()
            
            while time.time() - start_time < duration:
                # Collect comprehensive metrics
                sample = {
                    'timestamp': datetime.now().isoformat(),
                    'elapsed': time.time() - start_time,
                    'system': _collect_system_metrics(),
                    'disk_io': _collect_disk_io(),
                    'network': _collect_network_metrics(),
                    'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                }
                
                benchmark_data['samples'].append(sample)
                
                time.sleep(interval)
                pbar.update(interval)
    
    except KeyboardInterrupt:
        click.echo("\n🛑 Benchmark interrupted")
    
    benchmark_data['end_time'] = datetime.now().isoformat()
    
    if output == 'summary':
        _display_performance_summary(benchmark_data)
    elif output == 'json':
        click.echo(json.dumps(benchmark_data, indent=2, default=str))


def _collect_system_metrics() -> Dict:
    """Collect comprehensive system metrics."""
    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    cpu_freq = psutil.cpu_freq()
    cpu_count = psutil.cpu_count()
    
    # Memory metrics
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Load average (Unix-like systems)
    load_avg = None
    if hasattr(psutil, 'getloadavg'):
        load_avg = psutil.getloadavg()
    
    # Boot time
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    
    return {
        'cpu': {
            'percent': cpu_percent,
            'per_core': cpu_per_core,
            'frequency': {
                'current': cpu_freq.current if cpu_freq else None,
                'min': cpu_freq.min if cpu_freq else None,
                'max': cpu_freq.max if cpu_freq else None
            },
            'count': cpu_count
        },
        'memory': {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent,
            'used': memory.used,
            'free': memory.free,
            'buffers': getattr(memory, 'buffers', 0),
            'cached': getattr(memory, 'cached', 0)
        },
        'swap': {
            'total': swap.total,
            'used': swap.used,
            'free': swap.free,
            'percent': swap.percent
        },
        'load_avg': load_avg,
        'uptime': str(uptime),
        'boot_time': boot_time.isoformat()
    }


def _collect_process_metrics(top: int, sort_by: str, filter_user: str, 
                           filter_name: str, show_threads: bool, 
                           show_connections: bool) -> List[Dict]:
    """Collect process metrics."""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                   'memory_percent', 'memory_info', 'create_time',
                                   'status', 'num_threads']):
        try:
            proc_info = proc.info
            
            # Apply filters
            if filter_user and proc_info['username'] != filter_user:
                continue
            
            if filter_name and filter_name.lower() not in proc_info['name'].lower():
                continue
            
            # Add additional info if requested
            if show_threads:
                proc_info['num_threads'] = proc_info.get('num_threads', 0)
            
            if show_connections:
                try:
                    connections = proc.connections()
                    proc_info['connections'] = len(connections)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    proc_info['connections'] = 0
            
            processes.append(proc_info)
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Sort processes
    if sort_by == 'cpu':
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
    elif sort_by == 'memory':
        processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
    elif sort_by == 'pid':
        processes.sort(key=lambda x: x['pid'])
    elif sort_by == 'name':
        processes.sort(key=lambda x: x['name'].lower())
    
    return processes[:top]


def _collect_network_metrics(interface: Optional[str] = None) -> Dict:
    """Collect network metrics."""
    net_io = psutil.net_io_counters(pernic=True)
    
    if interface and interface in net_io:
        return {interface: net_io[interface]}
    
    return net_io


def _collect_disk_usage(paths: tuple, show_inodes: bool) -> List[Dict]:
    """Collect disk usage information."""
    disk_usage = []
    
    if paths:
        # Monitor specific paths
        for path in paths:
            try:
                usage = psutil.disk_usage(path)
                disk_info = {
                    'path': path,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100
                }
                
                if show_inodes:
                    # Get inode information (Unix-like systems)
                    try:
                        statvfs = os.statvfs(path)
                        disk_info['inodes'] = {
                            'total': statvfs.f_files,
                            'used': statvfs.f_files - statvfs.f_ffree,
                            'free': statvfs.f_ffree
                        }
                    except (AttributeError, OSError):
                        disk_info['inodes'] = None
                
                disk_usage.append(disk_info)
            except FileNotFoundError:
                continue
    else:
        # Monitor all mounted filesystems
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info = {
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100
                }
                
                if show_inodes:
                    try:
                        statvfs = os.statvfs(partition.mountpoint)
                        disk_info['inodes'] = {
                            'total': statvfs.f_files,
                            'used': statvfs.f_files - statvfs.f_ffree,
                            'free': statvfs.f_ffree
                        }
                    except (AttributeError, OSError):
                        disk_info['inodes'] = None
                
                disk_usage.append(disk_info)
            except (PermissionError, FileNotFoundError):
                continue
    
    return disk_usage


def _collect_disk_io() -> Dict:
    """Collect disk I/O statistics."""
    return psutil.disk_io_counters(perdisk=True)


def _calculate_network_rates(previous: Dict, current: Dict, time_delta: float) -> Dict:
    """Calculate network transfer rates."""
    rates = {}
    
    for interface in current:
        if interface in previous:
            prev_stats = previous[interface]
            curr_stats = current[interface]
            
            bytes_sent_rate = (curr_stats.bytes_sent - prev_stats.bytes_sent) / time_delta
            bytes_recv_rate = (curr_stats.bytes_recv - prev_stats.bytes_recv) / time_delta
            packets_sent_rate = (curr_stats.packets_sent - prev_stats.packets_sent) / time_delta
            packets_recv_rate = (curr_stats.packets_recv - prev_stats.packets_recv) / time_delta
            
            rates[interface] = {
                'bytes_sent_rate': bytes_sent_rate,
                'bytes_recv_rate': bytes_recv_rate,
                'packets_sent_rate': packets_sent_rate,
                'packets_recv_rate': packets_recv_rate,
                'total_bytes': curr_stats.bytes_sent + curr_stats.bytes_recv,
                'total_packets': curr_stats.packets_sent + curr_stats.packets_recv
            }
    
    return rates


def _calculate_disk_io_rates(previous: Dict, current: Dict, time_delta: float) -> Dict:
    """Calculate disk I/O rates."""
    rates = {}
    
    for disk in current:
        if disk in previous:
            prev_stats = previous[disk]
            curr_stats = current[disk]
            
            read_rate = (curr_stats.read_bytes - prev_stats.read_bytes) / time_delta
            write_rate = (curr_stats.write_bytes - prev_stats.write_bytes) / time_delta
            read_ops_rate = (curr_stats.read_count - prev_stats.read_count) / time_delta
            write_ops_rate = (curr_stats.write_count - prev_stats.write_count) / time_delta
            
            rates[disk] = {
                'read_rate': read_rate,
                'write_rate': write_rate,
                'read_ops_rate': read_ops_rate,
                'write_ops_rate': write_ops_rate,
                'total_io': read_rate + write_rate
            }
    
    return rates


def _check_alerts(metrics: Dict, cpu_threshold: float, 
                 memory_threshold: float, disk_threshold: float) -> List[Dict]:
    """Check for system alerts."""
    alerts = []
    timestamp = datetime.now().isoformat()
    
    # CPU alert
    if metrics['cpu']['percent'] > cpu_threshold:
        alerts.append({
            'type': 'cpu',
            'level': 'warning',
            'message': f"CPU usage high: {metrics['cpu']['percent']:.1f}%",
            'value': metrics['cpu']['percent'],
            'threshold': cpu_threshold,
            'timestamp': timestamp
        })
    
    # Memory alert
    if metrics['memory']['percent'] > memory_threshold:
        alerts.append({
            'type': 'memory',
            'level': 'warning',
            'message': f"Memory usage high: {metrics['memory']['percent']:.1f}%",
            'value': metrics['memory']['percent'],
            'threshold': memory_threshold,
            'timestamp': timestamp
        })
    
    return alerts


def _display_live_system_metrics(metrics: Dict, alerts: List[Dict]):
    """Display live system metrics."""
    # Clear screen and move cursor to top
    click.clear()
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    click.echo(f"🖥️ System Monitor - {current_time}")
    click.echo("=" * 60)
    
    # CPU info
    cpu = metrics['cpu']
    click.echo(f"💻 CPU: {cpu['percent']:6.1f}% ({cpu['count']} cores)")
    
    if cpu['frequency']['current']:
        click.echo(f"    Frequency: {cpu['frequency']['current']:.0f} MHz")
    
    # Memory info
    mem = metrics['memory']
    click.echo(f"🧠 Memory: {mem['percent']:6.1f}% ({_format_bytes(mem['used'])}/{_format_bytes(mem['total'])})")
    
    # Swap info
    swap = metrics['swap']
    if swap['total'] > 0:
        click.echo(f"💾 Swap: {swap['percent']:6.1f}% ({_format_bytes(swap['used'])}/{_format_bytes(swap['total'])})")
    
    # Load average
    if metrics['load_avg']:
        load = metrics['load_avg']
        click.echo(f"📊 Load: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}")
    
    # Uptime
    click.echo(f"⏰ Uptime: {metrics['uptime']}")
    
    # Alerts
    if alerts:
        click.echo("\n🚨 ALERTS:")
        for alert in alerts:
            click.echo(f"   {alert['message']}")


def _display_live_processes(processes: List[Dict], show_threads: bool, show_connections: bool):
    """Display live process information."""
    click.clear()
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    click.echo(f"📊 Process Monitor - {current_time}")
    click.echo("=" * 80)
    
    # Header
    header = f"{'PID':>8} {'USER':<12} {'CPU%':>6} {'MEM%':>6} {'NAME':<20}"
    if show_threads:
        header += f" {'THR':>4}"
    if show_connections:
        header += f" {'CONN':>5}"
    
    click.echo(header)
    click.echo("-" * len(header))
    
    # Process list
    for proc in processes:
        line = (f"{proc['pid']:>8} {proc['username']:<12} "
               f"{proc['cpu_percent'] or 0:>5.1f} {proc['memory_percent'] or 0:>5.1f} "
               f"{proc['name'][:20]:<20}")
        
        if show_threads:
            line += f" {proc.get('num_threads', 0):>4}"
        if show_connections:
            line += f" {proc.get('connections', 0):>5}"
        
        click.echo(line)


def _display_live_network_metrics(rates: Dict):
    """Display live network metrics."""
    click.clear()
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    click.echo(f"🌐 Network Monitor - {current_time}")
    click.echo("=" * 70)
    
    click.echo(f"{'Interface':<12} {'Sent/s':>12} {'Recv/s':>12} {'Total':>12}")
    click.echo("-" * 70)
    
    for interface, stats in rates.items():
        if interface == 'timestamp' or interface == 'elapsed':
            continue
        
        sent_rate = _format_bytes(stats['bytes_sent_rate'])
        recv_rate = _format_bytes(stats['bytes_recv_rate'])
        total = _format_bytes(stats['total_bytes'])
        
        click.echo(f"{interface:<12} {sent_rate:>12} {recv_rate:>12} {total:>12}")


def _display_live_disk_metrics(metrics: Dict, show_inodes: bool):
    """Display live disk metrics."""
    click.clear()
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    click.echo(f"💾 Disk Monitor - {current_time}")
    click.echo("=" * 80)
    
    # Disk usage
    click.echo("📁 Disk Usage:")
    header = f"{'Path/Device':<30} {'Used':>10} {'Free':>10} {'Total':>10} {'Use%':>6}"
    click.echo(header)
    click.echo("-" * len(header))
    
    for disk in metrics['usage']:
        path = disk.get('mountpoint', disk.get('path', disk.get('device', 'Unknown')))
        used = _format_bytes(disk['used'])
        free = _format_bytes(disk['free'])
        total = _format_bytes(disk['total'])
        percent = disk['percent']
        
        click.echo(f"{path[:29]:<30} {used:>10} {free:>10} {total:>10} {percent:>5.1f}%")
    
    # I/O rates
    if 'io_rates' in metrics:
        click.echo("\n📊 I/O Rates:")
        io_header = f"{'Disk':<15} {'Read/s':>12} {'Write/s':>12} {'Total/s':>12}"
        click.echo(io_header)
        click.echo("-" * len(io_header))
        
        for disk, rates in metrics['io_rates'].items():
            read_rate = _format_bytes(rates['read_rate'])
            write_rate = _format_bytes(rates['write_rate'])
            total_rate = _format_bytes(rates['total_io'])
            
            click.echo(f"{disk:<15} {read_rate:>12} {write_rate:>12} {total_rate:>12}")


def _display_system_summary(data_points: List[Dict], alerts: List[Dict]):
    """Display system monitoring summary."""
    click.echo("\n📊 Monitoring Summary")
    click.echo("=" * 40)
    
    if not data_points:
        return
    
    # Calculate averages
    cpu_values = [dp['cpu']['percent'] for dp in data_points]
    memory_values = [dp['memory']['percent'] for dp in data_points]
    
    click.echo(f"📈 CPU Usage:")
    click.echo(f"   Average: {sum(cpu_values) / len(cpu_values):.1f}%")
    click.echo(f"   Maximum: {max(cpu_values):.1f}%")
    click.echo(f"   Minimum: {min(cpu_values):.1f}%")
    
    click.echo(f"\n🧠 Memory Usage:")
    click.echo(f"   Average: {sum(memory_values) / len(memory_values):.1f}%")
    click.echo(f"   Maximum: {max(memory_values):.1f}%")
    click.echo(f"   Minimum: {min(memory_values):.1f}%")
    
    if alerts:
        click.echo(f"\n🚨 Total Alerts: {len(alerts)}")
        alert_types = {}
        for alert in alerts:
            alert_types[alert['type']] = alert_types.get(alert['type'], 0) + 1
        
        for alert_type, count in alert_types.items():
            click.echo(f"   {alert_type}: {count}")


def _display_network_summary(data_points: List[Dict]):
    """Display network monitoring summary."""
    click.echo("\n🌐 Network Summary")
    click.echo("=" * 40)
    
    if not data_points:
        return
    
    total_sent = 0
    total_recv = 0
    
    for dp in data_points:
        for interface, stats in dp.items():
            if interface in ['timestamp', 'elapsed']:
                continue
            total_sent += stats.get('bytes_sent_rate', 0)
            total_recv += stats.get('bytes_recv_rate', 0)
    
    avg_sent = total_sent / len(data_points)
    avg_recv = total_recv / len(data_points)
    
    click.echo(f"📤 Average sent: {_format_bytes(avg_sent)}/s")
    click.echo(f"📥 Average received: {_format_bytes(avg_recv)}/s")


def _display_performance_summary(benchmark_data: Dict):
    """Display performance benchmark summary."""
    click.echo("\n🏃 Performance Benchmark Results")
    click.echo("=" * 50)
    
    samples = benchmark_data['samples']
    if not samples:
        return
    
    # CPU statistics
    cpu_values = [sample['system']['cpu']['percent'] for sample in samples]
    click.echo(f"💻 CPU Performance:")
    click.echo(f"   Average: {sum(cpu_values) / len(cpu_values):.1f}%")
    click.echo(f"   Peak: {max(cpu_values):.1f}%")
    
    # Memory statistics
    memory_values = [sample['system']['memory']['percent'] for sample in samples]
    click.echo(f"\n🧠 Memory Performance:")
    click.echo(f"   Average: {sum(memory_values) / len(memory_values):.1f}%")
    click.echo(f"   Peak: {max(memory_values):.1f}%")
    
    # Load average (if available)
    load_values = [sample.get('load_avg', [0, 0, 0])[0] for sample in samples 
                  if sample.get('load_avg')]
    if load_values:
        click.echo(f"\n📊 Load Average:")
        click.echo(f"   Average: {sum(load_values) / len(load_values):.2f}")
        click.echo(f"   Peak: {max(load_values):.2f}")
    
    click.echo(f"\n⏰ Benchmark Duration: {benchmark_data['duration']} seconds")
    click.echo(f"📊 Total Samples: {len(samples)}")


def _save_monitoring_data(data_points: List[Dict], filepath: str, format_type: str):
    """Save monitoring data to file."""
    if format_type == 'json':
        with open(filepath, 'w') as f:
            json.dump(data_points, f, indent=2, default=str)
    elif format_type == 'csv':
        import csv
        
        if data_points:
            with open(filepath, 'w', newline='') as f:
                # Flatten first data point to get field names
                flattened = _flatten_dict(data_points[0])
                fieldnames = flattened.keys()
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for dp in data_points:
                    writer.writerow(_flatten_dict(dp))


def _flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _format_bytes(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}PB"
