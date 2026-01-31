"""
GPU Detection and FFmpeg Hardware Acceleration Support
"""

import subprocess
import re
import sys
from pathlib import Path


# Hide console window on Windows
SUBPROCESS_FLAGS = 0
if sys.platform == "win32":
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW


class GPUDetector:
    """Detect available GPU and FFmpeg hardware encoder support"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self._gpu_info = None
        self._ffmpeg_encoders = None
    
    def detect_gpu(self) -> dict:
        """
        Detect available GPU hardware
        
        Returns:
            dict with keys:
                - 'type': 'nvidia', 'amd', 'intel', or None
                - 'name': GPU name string
                - 'available': bool
        """
        if self._gpu_info is not None:
            return self._gpu_info
        
        gpu_info = {
            'type': None,
            'name': 'No GPU detected',
            'available': False
        }
        
        # Try NVIDIA first (most common for encoding)
        nvidia = self._detect_nvidia()
        if nvidia['available']:
            self._gpu_info = nvidia
            return nvidia
        
        # Try AMD
        amd = self._detect_amd()
        if amd['available']:
            self._gpu_info = amd
            return amd
        
        # Try Intel
        intel = self._detect_intel()
        if intel['available']:
            self._gpu_info = intel
            return intel
        
        self._gpu_info = gpu_info
        return gpu_info
    
    def _detect_nvidia(self) -> dict:
        """Detect NVIDIA GPU using nvidia-smi"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=SUBPROCESS_FLAGS
            )
            
            if result.returncode == 0 and result.stdout.strip():
                gpu_name = result.stdout.strip().split('\n')[0]
                return {
                    'type': 'nvidia',
                    'name': gpu_name,
                    'available': True
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Fallback: Try wmic on Windows
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=SUBPROCESS_FLAGS
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        line = line.strip()
                        if 'NVIDIA' in line or 'GeForce' in line or 'Quadro' in line or 'RTX' in line or 'GTX' in line:
                            return {
                                'type': 'nvidia',
                                'name': line,
                                'available': True
                            }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        return {'type': None, 'name': '', 'available': False}
    
    def _detect_amd(self) -> dict:
        """Detect AMD GPU"""
        # Windows: Use PowerShell (wmic deprecated in Windows 11)
        if sys.platform == "win32":
            try:
                # Try PowerShell Get-WmiObject first
                result = subprocess.run(
                    ['powershell', '-Command', 
                     'Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=SUBPROCESS_FLAGS
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if 'AMD' in line or 'Radeon' in line:
                            return {
                                'type': 'amd',
                                'name': line,
                                'available': True
                            }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # Fallback: Try wmic (older Windows)
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=SUBPROCESS_FLAGS
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        line = line.strip()
                        if 'AMD' in line or 'Radeon' in line:
                            return {
                                'type': 'amd',
                                'name': line,
                                'available': True
                            }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # Linux: Try lspci
        else:
            try:
                result = subprocess.run(
                    ['lspci'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'VGA' in line and ('AMD' in line or 'Radeon' in line):
                            # Extract GPU name
                            match = re.search(r':\s*(.+)$', line)
                            if match:
                                return {
                                    'type': 'amd',
                                    'name': match.group(1).strip(),
                                    'available': True
                                }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        return {'type': None, 'name': '', 'available': False}
    
    def _detect_intel(self) -> dict:
        """Detect Intel GPU"""
        # Windows: Use PowerShell (wmic deprecated in Windows 11)
        if sys.platform == "win32":
            try:
                # Try PowerShell Get-WmiObject first
                result = subprocess.run(
                    ['powershell', '-Command', 
                     'Get-WmiObject Win32_VideoController | Select-Object -ExpandProperty Name'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=SUBPROCESS_FLAGS
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        line = line.strip()
                        if 'Intel' in line and ('HD' in line or 'UHD' in line or 'Iris' in line or 'Arc' in line):
                            return {
                                'type': 'intel',
                                'name': line,
                                'available': True
                            }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            
            # Fallback: Try wmic (older Windows)
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=SUBPROCESS_FLAGS
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        line = line.strip()
                        if 'Intel' in line and ('HD' in line or 'UHD' in line or 'Iris' in line or 'Arc' in line):
                            return {
                                'type': 'intel',
                                'name': line,
                                'available': True
                            }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # Linux: Try lspci
        else:
            try:
                result = subprocess.run(
                    ['lspci'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'VGA' in line and 'Intel' in line:
                            match = re.search(r':\s*(.+)$', line)
                            if match:
                                return {
                                    'type': 'intel',
                                    'name': match.group(1).strip(),
                                    'available': True
                                }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        return {'type': None, 'name': '', 'available': False}
    
    def get_available_encoders(self) -> list:
        """
        Get list of available hardware encoders in FFmpeg
        
        Returns:
            list of encoder names (e.g., ['h264_nvenc', 'hevc_nvenc'])
        """
        if self._ffmpeg_encoders is not None:
            return self._ffmpeg_encoders
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=SUBPROCESS_FLAGS
            )
            
            if result.returncode == 0 or result.stderr:
                # FFmpeg outputs to stderr, not stdout
                output = result.stdout + result.stderr
                encoders = []
                
                # Parse encoder list - look for hardware encoders
                for line in output.split('\n'):
                    line = line.strip()
                    # Look for hardware encoder lines
                    if any(enc in line for enc in ['h264_nvenc', 'h264_amf', 'h264_qsv', 'h264_mf']):
                        # Extract encoder name (format: " V....D h264_nvenc ...")
                        parts = line.split()
                        if len(parts) >= 2:
                            encoder_name = parts[1]
                            if encoder_name.startswith('h264_'):
                                encoders.append(encoder_name)
                
                self._ffmpeg_encoders = encoders
                return encoders
        
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        self._ffmpeg_encoders = []
        return []
    
    def get_recommended_encoder(self) -> dict:
        """
        Get recommended encoder based on detected GPU
        
        Returns:
            dict with keys:
                - 'encoder': encoder name (e.g., 'h264_nvenc') or None
                - 'preset': preset value (e.g., 'p4')
                - 'available': bool
                - 'reason': explanation string
        """
        gpu = self.detect_gpu()
        encoders = self.get_available_encoders()
        
        if not gpu['available']:
            return {
                'encoder': None,
                'preset': None,
                'available': False,
                'reason': 'No GPU detected'
            }
        
        # Map GPU type to encoder
        encoder_map = {
            'nvidia': 'h264_nvenc',
            'amd': 'h264_amf',
            'intel': 'h264_qsv'
        }
        
        preset_map = {
            'nvidia': 'p4',  # p1-p7, p4 is balanced
            'amd': 'balanced',
            'intel': 'balanced'
        }
        
        recommended_encoder = encoder_map.get(gpu['type'])
        
        if recommended_encoder in encoders:
            return {
                'encoder': recommended_encoder,
                'preset': preset_map.get(gpu['type']),
                'available': True,
                'reason': f"Using {gpu['name']}"
            }
        else:
            return {
                'encoder': None,
                'preset': None,
                'available': False,
                'reason': f"GPU detected ({gpu['name']}) but FFmpeg doesn't support {recommended_encoder}"
            }
    
    def get_encoder_args(self, use_gpu: bool = True) -> list:
        """
        Get FFmpeg encoder arguments
        
        Args:
            use_gpu: Whether to use GPU acceleration
        
        Returns:
            list of FFmpeg arguments for video encoding
        """
        if not use_gpu:
            # CPU encoding (default)
            return ['-c:v', 'libx264', '-preset', 'fast', '-crf', '18']
        
        recommendation = self.get_recommended_encoder()
        
        if not recommendation['available']:
            # Fallback to CPU
            return ['-c:v', 'libx264', '-preset', 'fast', '-crf', '18']
        
        encoder = recommendation['encoder']
        preset = recommendation['preset']
        
        # Build encoder-specific arguments
        if encoder == 'h264_nvenc':
            # NVIDIA NVENC
            # -pix_fmt yuv420p required for compatibility with various source formats
            return [
                '-c:v', 'h264_nvenc',
                '-preset', preset,
                '-rc', 'vbr',
                '-cq', '19',  # Similar quality to CRF 18
                '-b:v', '0',  # Variable bitrate
                '-pix_fmt', 'yuv420p'
            ]
        
        elif encoder == 'h264_amf':
            # AMD AMF
            # -pix_fmt yuv420p required for compatibility with various source formats
            return [
                '-c:v', 'h264_amf',
                '-quality', preset,
                '-rc', 'vbr_latency',
                '-qp_i', '18',
                '-qp_p', '19',
                '-pix_fmt', 'yuv420p'
            ]
        
        elif encoder == 'h264_qsv':
            # Intel QSV
            # -pix_fmt yuv420p required for compatibility with various source formats
            return [
                '-c:v', 'h264_qsv',
                '-preset', preset,
                '-global_quality', '19',
                '-pix_fmt', 'yuv420p'
            ]
        
        # Fallback to CPU
        return ['-c:v', 'libx264', '-preset', 'fast', '-crf', '18']
