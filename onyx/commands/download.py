"""
Download command for file downloading with progress tracking.
"""

import os
import hashlib
import json
import time
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import click
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm


@click.group()
def download():
    """Download files with progress tracking and resume support."""
    pass


@download.command()
@click.argument('url')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output filename or directory')
@click.option('--resume', '-r', is_flag=True, help='Resume partial downloads')
@click.option('--chunk-size', type=int, default=8192, help='Download chunk size in bytes')
@click.option('--timeout', '-t', type=int, default=30, help='Request timeout in seconds')
@click.option('--retries', type=int, default=3, help='Number of retry attempts')
@click.option('--user-agent', '-u', help='Custom User-Agent string')
@click.option('--headers', '-h', multiple=True, help='Custom headers (format: "Key: Value")')
@click.option('--verify-ssl', is_flag=True, default=True, help='Verify SSL certificates')
@click.option('--max-size', type=str, help='Maximum file size to download (e.g., 100MB)')
@click.option('--checksum', '-c', help='Expected checksum (MD5, SHA1, or SHA256)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
def single(url: str, output: Path, resume: bool, chunk_size: int, timeout: int, 
          retries: int, user_agent: str, headers: tuple, verify_ssl: bool, 
          max_size: str, checksum: str, quiet: bool):
    """Download a single file from URL."""
    
    if not quiet:
        click.echo(f"🔗 Downloading: {url}")
    
    try:
        # Parse max size
        max_size_bytes = _parse_size(max_size) if max_size else None
        if max_size_bytes and not quiet:
            click.echo(f"📏 Max size: {_format_bytes(max_size_bytes)}")
        
        # Setup session
        session = _create_session(timeout, retries, user_agent, headers, verify_ssl)
        
        # Determine output path (try headers first, then URL)
        output = _derive_output_path(session, url, output)
        
        if not quiet:
            click.echo(f"💾 Output: {output}")
        
        # Check if file exists and resume is requested
        start_byte = 0
        if resume and output.exists():
            start_byte = output.stat().st_size
            if not quiet:
                click.echo(f"🔄 Resuming from byte {start_byte}")
        
        # Download the file
        success = _download_file(
            session, url, output, start_byte, chunk_size, 
            max_size_bytes, quiet
        )
        
        if success:
            # Verify checksum if provided
            if checksum:
                if not quiet:
                    click.echo("🔍 Verifying checksum...")
                
                if _verify_checksum(output, checksum):
                    if not quiet:
                        click.echo("✅ Checksum verification passed")
                else:
                    click.echo("❌ Checksum verification failed", err=True)
                    return
            
            file_size = output.stat().st_size
            if not quiet:
                click.echo(f"✅ Download completed: {_format_bytes(file_size)}")
        else:
            if not quiet:
                click.echo("❌ Download failed", err=True)
    
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


@download.command()
@click.argument('urls_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output-dir', '-o', type=click.Path(path_type=Path), default=Path('.'), help='Output directory')
@click.option('--workers', '-w', type=int, default=4, help='Number of concurrent downloads')
@click.option('--resume', '-r', is_flag=True, help='Resume partial downloads')
@click.option('--timeout', '-t', type=int, default=30, help='Request timeout in seconds')
@click.option('--retries', type=int, default=3, help='Number of retry attempts')
@click.option('--user-agent', '-u', help='Custom User-Agent string')
@click.option('--verify-ssl', is_flag=True, default=True, help='Verify SSL certificates')
@click.option('--continue-on-error', is_flag=True, help='Continue downloading other files if one fails')
@click.option('--output', '--output-format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
def batch(urls_file: Path, output_dir: Path, workers: int, resume: bool, timeout: int,
         retries: int, user_agent: str, verify_ssl: bool, continue_on_error: bool,
         output_format: str):
    """Download multiple files from a list of URLs."""
    
    # Read URLs from file
    try:
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        click.echo(f"❌ Error reading URLs file: {e}", err=True)
        return
    
    if not urls:
        click.echo("❌ No URLs found in file", err=True)
        return
    
    if output_format == 'table':
        click.echo(f"📦 Batch download: {len(urls)} files")
        click.echo(f"📁 Output directory: {output_dir}")
        click.echo(f"👥 Workers: {workers}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download files concurrently
    results = []
    failed_downloads = []
    
    def download_single_url(url: str) -> Dict:
        """Download a single URL and return result."""
        try:
            session = _create_session(timeout, retries, user_agent, [], verify_ssl)
            filename = _extract_filename_from_url(url)
            output_path = output_dir / filename
            
            start_byte = 0
            if resume and output_path.exists():
                start_byte = output_path.stat().st_size
            
            start_time = time.time()
            success = _download_file(session, url, output_path, start_byte, 8192, None, True)
            end_time = time.time()
            
            if success:
                file_size = output_path.stat().st_size
                return {
                    'url': url,
                    'filename': filename,
                    'status': 'success',
                    'size': file_size,
                    'duration': end_time - start_time
                }
            else:
                return {
                    'url': url,
                    'filename': filename,
                    'status': 'failed',
                    'error': 'Download failed'
                }
        
        except Exception as e:
            return {
                'url': url,
                'filename': _extract_filename_from_url(url),
                'status': 'error',
                'error': str(e)
            }
    
    # Use ThreadPoolExecutor for concurrent downloads
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all download tasks
        future_to_url = {executor.submit(download_single_url, url): url for url in urls}
        
        # Process completed downloads with progress bar
        with tqdm(total=len(urls), desc="Downloading", unit="file") as pbar:
            for future in as_completed(future_to_url):
                result = future.result()
                results.append(result)
                
                if result['status'] == 'success':
                    pbar.set_postfix_str(f"✅ {result['filename']}")
                else:
                    failed_downloads.append(result)
                    pbar.set_postfix_str(f"❌ {result['filename']}")
                    
                    if not continue_on_error:
                        # Cancel remaining downloads
                        for remaining_future in future_to_url:
                            remaining_future.cancel()
                        break
                
                pbar.update(1)
    
    # Display results
    successful_downloads = [r for r in results if r['status'] == 'success']
    
    if output_format == 'table':
        click.echo(f"\n📊 Download Summary:")
        click.echo(f"   ✅ Successful: {len(successful_downloads)}")
        click.echo(f"   ❌ Failed: {len(failed_downloads)}")
        
        if successful_downloads:
            total_size = sum(r['size'] for r in successful_downloads)
            total_time = sum(r['duration'] for r in successful_downloads)
            avg_speed = total_size / total_time if total_time > 0 else 0
            
            click.echo(f"   📦 Total size: {_format_bytes(total_size)}")
            click.echo(f"   ⏱️ Total time: {total_time:.1f}s")
            click.echo(f"   🚀 Average speed: {_format_bytes(avg_speed)}/s")
        
        if failed_downloads:
            click.echo(f"\n❌ Failed downloads:")
            for failure in failed_downloads:
                click.echo(f"   {failure['url']} - {failure['error']}")
    
    elif output_format == 'json':
        summary = {
            'total_urls': len(urls),
            'successful': len(successful_downloads),
            'failed': len(failed_downloads),
            'results': results
        }
        click.echo(json.dumps(summary, indent=2))


@download.command()
@click.argument('url')
@click.option('--parts', '-p', type=int, default=4, help='Number of parts to download simultaneously')
@click.option('--output', '-o', type=click.Path(path_type=Path), help='Output filename')
@click.option('--timeout', '-t', type=int, default=30, help='Request timeout in seconds')
@click.option('--retries', type=int, default=3, help='Number of retry attempts')
@click.option('--user-agent', '-u', help='Custom User-Agent string')
@click.option('--verify-ssl', is_flag=True, default=True, help='Verify SSL certificates')
def accelerated(url: str, parts: int, output: Path, timeout: int, retries: int,
               user_agent: str, verify_ssl: bool):
    """Download file using multiple connections for acceleration."""
    
    click.echo(f"🚀 Accelerated download: {url}")
    click.echo(f"🔗 Parts: {parts}")
    
    try:
        # Setup session
        session = _create_session(timeout, retries, user_agent, [], verify_ssl)
        
        # Get file info
        head_response = session.head(url, allow_redirects=True)
        head_response.raise_for_status()
        
        # Check if server supports range requests
        accept_ranges = head_response.headers.get('Accept-Ranges', '').lower()
        if accept_ranges != 'bytes':
            click.echo("⚠️ Server doesn't support range requests, falling back to single connection")
            
            # Determine output path
            if output is None:
                filename = _extract_filename_from_url(url)
                output = Path(filename)
            
            success = _download_file(session, url, output, 0, 8192, None, False)
            
            if success:
                file_size = output.stat().st_size
                click.echo(f"✅ Download completed: {_format_bytes(file_size)}")
            else:
                click.echo("❌ Download failed", err=True)
            return
        
        # Get file size
        content_length = head_response.headers.get('Content-Length')
        if not content_length:
            click.echo("❌ Cannot determine file size for accelerated download", err=True)
            return
        
        file_size = int(content_length)
        click.echo(f"📏 File size: {_format_bytes(file_size)}")
        
        # Determine output path
        if output is None:
            filename = _extract_filename_from_url(url)
            output = Path(filename)
        
        # Calculate part sizes
        part_size = file_size // parts
        ranges = []
        
        for i in range(parts):
            start = i * part_size
            end = start + part_size - 1
            if i == parts - 1:  # Last part gets remaining bytes
                end = file_size - 1
            ranges.append((start, end))
        
        click.echo(f"📦 Downloading {parts} parts of {_format_bytes(part_size)} each")
        
        # Download parts concurrently
        part_files = []
        
        def download_part(part_num: int, start: int, end: int) -> bool:
            """Download a single part of the file."""
            part_session = _create_session(timeout, retries, user_agent, [], verify_ssl)
            headers = {'Range': f'bytes={start}-{end}'}
            
            part_filename = f"{output}.part{part_num}"
            part_files.append(part_filename)
            
            try:
                response = part_session.get(url, headers=headers, stream=True)
                response.raise_for_status()
                
                with open(part_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return True
            except Exception:
                return False
        
        # Download all parts
        with ThreadPoolExecutor(max_workers=parts) as executor:
            futures = [
                executor.submit(download_part, i, start, end)
                for i, (start, end) in enumerate(ranges)
            ]
            
            with tqdm(total=parts, desc="Downloading parts") as pbar:
                all_success = True
                for future in as_completed(futures):
                    success = future.result()
                    if not success:
                        all_success = False
                    pbar.update(1)
        
        if not all_success:
            click.echo("❌ Some parts failed to download", err=True)
            # Cleanup partial files
            for part_file in part_files:
                Path(part_file).unlink(missing_ok=True)
            return
        
        # Combine parts
        click.echo("🔗 Combining parts...")
        with open(output, 'wb') as outfile:
            for i in range(parts):
                part_filename = f"{output}.part{i}"
                with open(part_filename, 'rb') as part_file:
                    outfile.write(part_file.read())
                
                # Remove part file
                Path(part_filename).unlink()
        
        final_size = output.stat().st_size
        click.echo(f"✅ Accelerated download completed: {_format_bytes(final_size)}")
    
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


def _create_session(timeout: int, retries: int, user_agent: str, 
                   headers: List[str], verify_ssl: bool) -> requests.Session:
    """Create a configured requests session."""
    session = requests.Session()
    
    # Configure retries (urllib3>=2 uses 'allowed_methods', older uses 'method_whitelist')
    try:
        retry_strategy = Retry(
            total=retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
    except TypeError:
        # Fallback for urllib3<2
        retry_strategy = Retry(
            total=retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set timeout
    session.timeout = timeout
    
    # Set SSL verification
    session.verify = verify_ssl
    
    # Set user agent
    if user_agent:
        session.headers.update({'User-Agent': user_agent})
    else:
        session.headers.update({'User-Agent': 'Onyx-Download/1.0'})
    
    # Add custom headers
    for header in headers:
        if ':' in header:
            key, value = header.split(':', 1)
            session.headers.update({key.strip(): value.strip()})
    
    return session


def _extract_filename_from_url(url: str) -> str:
    """Extract filename from URL."""
    parsed = urlparse(url)
    filename = unquote(parsed.path.split('/')[-1])
    
    if not filename or '.' not in filename:
        filename = 'download'
    
    return filename


def _filename_from_disposition(disposition: Optional[str]) -> Optional[str]:
    """Try to extract filename from Content-Disposition header (RFC 6266)."""
    if not disposition:
        return None
    # filename*="UTF-8''..."
    match = re.search(r"filename\*\s*=\s*UTF-8''([^;]+)", disposition, re.IGNORECASE)
    if match:
        return _sanitize_filename(_repair_mojibake(unquote(match.group(1).strip('"'))))
    # filename="..."
    match = re.search(r'filename\s*=\s*"([^"]+)"', disposition, re.IGNORECASE)
    if match:
        return _sanitize_filename(_repair_mojibake(unquote(match.group(1))))
    # filename=...
    match = re.search(r'filename\s*=\s*([^;]+)', disposition, re.IGNORECASE)
    if match:
        return _sanitize_filename(_repair_mojibake(unquote(match.group(1).strip('"'))))
    return None


def _derive_output_path(session: requests.Session, url: str, output: Optional[Path]) -> Path:
    """Determine final output path using headers or URL.
    Priority: explicit output file > output dir + detected name > detected name in CWD.
    """
    # If explicit file path provided and not a directory
    if output and (output.suffix or (output.exists() and output.is_file())):
        return output

    # Try to get filename from HEAD (Content-Disposition or final URL)
    filename = None
    try:
        head = session.head(url, allow_redirects=True)
        cd = head.headers.get('Content-Disposition')
        filename = _filename_from_disposition(cd)
        if not filename:
            filename = _extract_filename_from_url(head.url)
    except Exception:
        pass

    if not filename or filename == 'download':
        filename = _extract_filename_from_url(url)
    else:
        filename = _sanitize_filename(_repair_mojibake(filename))

    if output and output.is_dir():
        return output / filename
    elif output is None:
        return Path(filename)
    else:
        # output given but is directory-like without existence; treat as dir
        return Path(output) / filename


_INVALID_WIN_CHARS = r'<>:"/\\|?*'

def _sanitize_filename(name: str) -> str:
    """Remove characters invalid on Windows and trim spaces/dots."""
    cleaned = ''.join('_' if ch in _INVALID_WIN_CHARS else ch for ch in name)
    cleaned = cleaned.strip(' .')
    return cleaned or 'download'


def _repair_mojibake(text: str) -> str:
    """Attempt to fix mojibake from ISO-8859-1 decoded UTF-8 (common on Windows).

    If typical sequences like 'Ã', 'Ð', 'Ñ' appear, try latin1->utf8 roundtrip.
    """
    if any(sym in text for sym in ('Ã', 'Ð', 'Ñ', 'Ò', 'Â')):
        try:
            return text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore') or text
        except Exception:
            return text
    return text


def _download_file(session: requests.Session, url: str, output_path: Path,
                  start_byte: int, chunk_size: int, max_size: Optional[int],
                  quiet: bool) -> bool:
    """Download a file with progress tracking."""
    try:
        # Set up headers for resume
        headers = {}
        if start_byte > 0:
            headers['Range'] = f'bytes={start_byte}-'
        
        # Start download
        response = session.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        # Get total file size
        if 'Content-Range' in response.headers:
            # Partial content
            range_info = response.headers['Content-Range']
            total_size = int(range_info.split('/')[-1])
        else:
            # Full content
            total_size = int(response.headers.get('Content-Length', 0))
            if start_byte > 0:
                total_size += start_byte
        
        # Check max size limit
        if max_size and total_size > max_size:
            if not quiet:
                click.echo(f"❌ File size ({_format_bytes(total_size)}) exceeds limit ({_format_bytes(max_size)})")
            return False
        
        # Open file for writing
        mode = 'ab' if start_byte > 0 else 'wb'
        
        with open(output_path, mode) as f:
            if quiet:
                # Download without progress bar
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
            else:
                # Download with progress bar
                with tqdm(
                    total=total_size,
                    initial=start_byte,
                    unit='B',
                    unit_scale=True,
                    desc=f"Downloading {output_path.name}"
                ) as pbar:
                    
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        
        return True
    
    except Exception as e:
        if not quiet:
            click.echo(f"❌ Download error: {e}")
        return False


def _parse_size(size_str: str) -> int:
    """Parse size string to bytes."""
    size_str = size_str.upper()
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024**2,
        'GB': 1024**3,
        'TB': 1024**4
    }
    
    for unit, multiplier in multipliers.items():
        if size_str.endswith(unit):
            try:
                value = float(size_str[:-len(unit)])
                return int(value * multiplier)
            except ValueError:
                break
    
    # Default to bytes if no unit specified
    try:
        return int(size_str)
    except ValueError:
        raise ValueError(f"Invalid size format: {size_str}")


def _format_bytes(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def _verify_checksum(file_path: Path, expected_checksum: str) -> bool:
    """Verify file checksum."""
    expected_checksum = expected_checksum.lower()
    
    # Determine hash algorithm based on checksum length
    if len(expected_checksum) == 32:
        hash_algo = hashlib.md5()
    elif len(expected_checksum) == 40:
        hash_algo = hashlib.sha1()
    elif len(expected_checksum) == 64:
        hash_algo = hashlib.sha256()
    else:
        raise ValueError("Unsupported checksum format")
    
    # Calculate file hash
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_algo.update(chunk)
    
    actual_checksum = hash_algo.hexdigest()
    return actual_checksum == expected_checksum
