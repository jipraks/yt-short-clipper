"""
Dependency Manager - Auto download and setup FFmpeg and Deno
"""

import sys
import os
import platform
import urllib.request
import zipfile
import tarfile
import shutil
from pathlib import Path
from datetime import datetime


def _log_to_file(msg):
    """Write log directly to error.log file"""
    try:
        # Get app directory
        if getattr(sys, 'frozen', False):
            app_dir = Path(sys.executable).parent
        else:
            app_dir = Path(__file__).parent.parent
        
        log_file = app_dir / "error.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [DOWNLOAD] {msg}\n")
    except:
        pass


def debug_log(msg):
    """Log message to both console and file"""
    print(f"[DEBUG] {msg}")
    _log_to_file(msg)


def get_os_info():
    """Get OS and architecture information
    
    Returns:
        tuple: (os_type, arch) where:
            os_type: 'windows', 'linux', 'darwin' (macOS)
            arch: 'x86_64', 'aarch64', 'arm64'
    """
    os_type = sys.platform
    if os_type.startswith('win'):
        os_type = 'windows'
    elif os_type.startswith('linux'):
        os_type = 'linux'
    elif os_type.startswith('darwin'):
        os_type = 'darwin'
    
    machine = platform.machine().lower()
    if machine in ['amd64', 'x86_64', 'x64']:
        arch = 'x86_64'
    elif machine in ['arm64', 'aarch64']:
        arch = 'aarch64'
    else:
        arch = machine
    
    return os_type, arch


def get_ffmpeg_download_url():
    """Get FFmpeg download URL based on OS
    
    Returns:
        tuple: (url, filename) or (None, None) if unsupported
    """
    os_type, arch = get_os_info()
    
    if os_type == 'windows':
        if arch == 'x86_64':
            # Use GyanD full build from GitHub - includes all codecs + hardware encoders (AMF, NVENC, QSV)
            url = "https://github.com/GyanD/codexffmpeg/releases/download/2026-01-29-git-c898ddb8fe/ffmpeg-2026-01-29-git-c898ddb8fe-full_build.zip"
            filename = "ffmpeg-full_build.zip"
        else:
            # Fallback to BtbN for ARM
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-winarm64-gpl.zip"
            filename = "ffmpeg-master-latest-winarm64-gpl.zip"
    elif os_type == 'linux':
        # BtbN builds for Linux
        base_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
        if arch == 'x86_64':
            filename = "ffmpeg-master-latest-linux64-gpl.tar.xz"
        elif arch == 'aarch64':
            filename = "ffmpeg-master-latest-linuxarm64-gpl.tar.xz"
        else:
            return None, None
        url = base_url + filename
    elif os_type == 'darwin':
        # FFmpeg-Builds doesn't have macOS builds, return None
        # User needs to install via homebrew: brew install ffmpeg
        return None, None
    else:
        return None, None
    
    return url, filename


def get_deno_download_url():
    """Get Deno download URL based on OS
    
    Returns:
        tuple: (url, filename) or (None, None) if unsupported
    """
    os_type, arch = get_os_info()
    
    # Use latest stable version
    version = "v2.6.7"
    base_url = f"https://github.com/denoland/deno/releases/download/{version}/"
    
    if os_type == 'windows':
        if arch == 'x86_64':
            filename = "deno-x86_64-pc-windows-msvc.zip"
        else:
            return None, None
    elif os_type == 'linux':
        if arch == 'x86_64':
            filename = "deno-x86_64-unknown-linux-gnu.zip"
        elif arch == 'aarch64':
            filename = "deno-aarch64-unknown-linux-gnu.zip"
        else:
            return None, None
    elif os_type == 'darwin':
        if arch == 'x86_64':
            filename = "deno-x86_64-apple-darwin.zip"
        elif arch == 'aarch64':
            filename = "deno-aarch64-apple-darwin.zip"
        else:
            return None, None
    else:
        return None, None
    
    return base_url + filename, filename


def download_file(url: str, dest_path: Path, progress_callback=None):
    """Download file with progress tracking
    
    Args:
        url: Download URL
        dest_path: Destination file path
        progress_callback: Optional callback(downloaded, total) for progress
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        debug_log(f"Downloading from: {url}")
        
        # Create parent directory if not exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create SSL context - try with certifi first, then unverified as fallback
        import ssl
        
        ssl_context = None
        
        # Try to use certifi certificates first
        try:
            import certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            debug_log("Using certifi SSL certificates")
        except ImportError:
            debug_log("certifi not available, trying default SSL context")
        
        # If certifi not available, try default context
        if ssl_context is None:
            try:
                ssl_context = ssl.create_default_context()
            except Exception as e:
                debug_log(f"Default SSL context failed: {e}")
        
        # If still failing, use unverified context (less secure but works)
        if ssl_context is None:
            ssl_context = ssl._create_unverified_context()
            debug_log("Using unverified SSL context (fallback)")
        
        # Create request with User-Agent header (GitHub requires this)
        request = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        try:
            response = urllib.request.urlopen(request, context=ssl_context, timeout=120)
        except ssl.SSLCertVerificationError:
            # Fallback to unverified context if SSL verification fails
            debug_log("SSL verification failed, using unverified context")
            ssl_context = ssl._create_unverified_context()
            response = urllib.request.urlopen(request, context=ssl_context, timeout=120)
        
        total_size = int(response.headers.get('Content-Length', 0))
        debug_log(f"Total size: {total_size} bytes")
        
        downloaded = 0
        block_size = 8192
        
        with open(dest_path, 'wb') as f:
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                
                downloaded += len(buffer)
                f.write(buffer)
                
                if progress_callback:
                    progress_callback(downloaded, total_size)
        
        response.close()
        debug_log(f"Downloaded to: {dest_path}")
        return True
        
    except Exception as e:
        debug_log(f"Download error: {e}")
        import traceback
        debug_log(traceback.format_exc())
        return False


def extract_zip(zip_path: Path, extract_to: Path):
    """Extract ZIP file
    
    Args:
        zip_path: Path to ZIP file
        extract_to: Extraction destination directory
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        debug_log(f"Extracting ZIP: {zip_path}")
        extract_to.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        debug_log(f"Extracted to: {extract_to}")
        return True
        
    except Exception as e:
        debug_log(f"Extract error: {e}")
        return False


def extract_tar_xz(tar_path: Path, extract_to: Path):
    """Extract TAR.XZ file
    
    Args:
        tar_path: Path to TAR.XZ file
        extract_to: Extraction destination directory
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        debug_log(f"Extracting TAR.XZ: {tar_path}")
        extract_to.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:xz') as tar_ref:
            tar_ref.extractall(extract_to)
        
        debug_log(f"Extracted to: {extract_to}")
        return True
        
    except Exception as e:
        debug_log(f"Extract error: {e}")
        return False


def setup_ffmpeg(app_dir: Path, progress_callback=None) -> bool:
    """Download and setup FFmpeg
    
    Args:
        app_dir: Application directory
        progress_callback: Optional callback(downloaded, total) for progress
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url, filename = get_ffmpeg_download_url()
        
        if not url:
            debug_log("FFmpeg auto-download not supported for this OS")
            return False
        
        # Download
        download_path = app_dir / "_temp" / filename
        if not download_file(url, download_path, progress_callback):
            return False
        
        # Extract
        extract_dir = app_dir / "_temp" / "ffmpeg_extract"
        if filename.endswith('.zip'):
            if not extract_zip(download_path, extract_dir):
                return False
        elif filename.endswith('.tar.xz'):
            if not extract_tar_xz(download_path, extract_dir):
                return False
        
        # Find ffmpeg executable in extracted files
        ffmpeg_dir = app_dir / "ffmpeg"
        ffmpeg_dir.mkdir(parents=True, exist_ok=True)
        
        os_type, _ = get_os_info()
        exe_name = "ffmpeg.exe" if os_type == 'windows' else "ffmpeg"
        
        # Search for ffmpeg executable recursively
        found = False
        for root, dirs, files in os.walk(extract_dir):
            if exe_name in files:
                src = Path(root) / exe_name
                dest = ffmpeg_dir / exe_name
                shutil.copy2(src, dest)
                debug_log(f"FFmpeg copied to: {dest}")
                found = True
                
                # Also copy ffprobe if exists
                probe_name = "ffprobe.exe" if os_type == 'windows' else "ffprobe"
                probe_src = Path(root) / probe_name
                if probe_src.exists():
                    probe_dest = ffmpeg_dir / probe_name
                    shutil.copy2(probe_src, probe_dest)
                    debug_log(f"FFprobe copied to: {probe_dest}")
                
                break
        
        if not found:
            debug_log("FFmpeg executable not found in extracted files")
            return False
        
        # Cleanup
        shutil.rmtree(extract_dir, ignore_errors=True)
        download_path.unlink(missing_ok=True)
        
        return True
        
    except Exception as e:
        debug_log(f"FFmpeg setup error: {e}")
        return False


def setup_deno(app_dir: Path, progress_callback=None) -> bool:
    """Download and setup Deno
    
    Args:
        app_dir: Application directory
        progress_callback: Optional callback(downloaded, total) for progress
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        url, filename = get_deno_download_url()
        
        if not url:
            debug_log("Deno auto-download not supported for this OS")
            return False
        
        # Download
        download_path = app_dir / "_temp" / filename
        if not download_file(url, download_path, progress_callback):
            return False
        
        # Extract
        extract_dir = app_dir / "_temp" / "deno_extract"
        if not extract_zip(download_path, extract_dir):
            return False
        
        # Move deno executable to bin folder
        bin_dir = app_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        os_type, _ = get_os_info()
        exe_name = "deno.exe" if os_type == 'windows' else "deno"
        
        src = extract_dir / exe_name
        dest = bin_dir / exe_name
        
        if src.exists():
            shutil.copy2(src, dest)
            debug_log(f"Deno copied to: {dest}")
            
            # Make executable on Unix systems
            if os_type != 'windows':
                import os
                os.chmod(dest, 0o755)
        
        # Cleanup
        shutil.rmtree(extract_dir, ignore_errors=True)
        download_path.unlink(missing_ok=True)
        
        return True
        
    except Exception as e:
        debug_log(f"Deno setup error: {e}")
        return False


def check_dependency(name: str, app_dir: Path) -> bool:
    """Check if dependency is installed
    
    Args:
        name: Dependency name ('ffmpeg' or 'deno')
        app_dir: Application directory
    
    Returns:
        bool: True if installed, False otherwise
    """
    os_type, _ = get_os_info()
    
    if name == 'ffmpeg':
        exe_name = "ffmpeg.exe" if os_type == 'windows' else "ffmpeg"
        path = app_dir / "ffmpeg" / exe_name
        return path.exists()
    
    elif name == 'deno':
        exe_name = "deno.exe" if os_type == 'windows' else "deno"
        path = app_dir / "bin" / exe_name
        return path.exists()
    
    return False
