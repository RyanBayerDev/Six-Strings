@echo off
rem Starts Ollama for Six Strings with CUDA disabled.
rem (On this laptop the NVIDIA driver is older than Ollama's CUDA build, which crashes
rem  with "device kernel image is invalid". Ollama still uses the GPU through Vulkan.)
rem If you still get GPU errors, remove "rem" from the OLLAMA_VULKAN line to force CPU only.

taskkill /IM "ollama app.exe" /F >nul 2>&1
taskkill /IM ollama.exe /F >nul 2>&1

set CUDA_VISIBLE_DEVICES=-1
rem set OLLAMA_VULKAN=0

echo Starting Ollama on http://127.0.0.1:11434 ... leave this window open.
"%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
pause
