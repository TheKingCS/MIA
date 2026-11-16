# MIA OS proofs of concept

The six tests that settle what Prompt 05 couldn't decide on paper
(`docs/mia_os/MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md` section 2). Zac said yes to running them (Q-49,
2026-11-16). What runs where:

| Test | Where | State |
|---|---|---|
| 1. The graphics card under Linux | **Zac at the PC**, from a USB stick (below) | ready to run |
| 2. The image: build | GitHub's machines (`.github/workflows/mia-os-poc.yml`, job `image`) | runs on every change to `os/` |
| 2. The image: boot, update, roll back | a virtual machine | not yet |
| 3. MIA's session: KDE's compositor against cage | a virtual machine | not yet |
| 4. The runtime as a Linux service | GitHub's machines (job `runtime-service`), the suite on Linux (job `suite-linux`) | runs on every change |
| 5. The system helper | a virtual machine, once a first helper exists | not yet |
| 6. Narrowing file reach with Landlock | GitHub's machines (job `landlock`, `landlock_probe.py`) | runs on every change |

## Test 1: the graphics card under Linux (about an hour, nothing installed)

What it settles: whether Fedora runs MIA's models on the RX 7900 XTX as well as Windows does. The bar is the 14B
model writing at 65 tokens a second or more (Windows: 73). Nothing is installed on the PC: Fedora runs from the
USB stick, in memory, and is gone when you restart. Windows isn't touched.

**You need:** a USB stick of 8 GB or more (it will be erased), another computer or the PC under Windows to prepare
it, and the internet.

1. **Make the stick.** On Windows, install *Fedora Media Writer* from fedoraproject.org, choose **Fedora KDE Plasma
   Desktop** version **45**, and write it to the stick.
2. **Start from it.** Restart the PC and press the boot-menu key as it starts (often F8, F11 or F12 on AM5 boards;
   the screen says which). Pick the USB stick. If it won't start, Secure Boot is fine with Fedora; check the stick
   is chosen in UEFI mode.
3. Choose **Start Fedora-KDE-Live**. **Don't** click "Install to hard drive".
4. Connect to the internet (Wi-Fi top-right, or a cable). Open **Konsole** (the terminal).
5. **Install the model runner into the live session** (it lives in memory only):
   ```
   sudo dnf install -y ollama ollama-rocm
   ```
6. **Get the models.** Two ways:
   - *Use the ones already on Windows (no download, read-only).* Find the Windows drive with `lsblk -f` (the large
     `ntfs` partition), then:
     ```
     sudo mkdir -p /mnt/win && sudo mount -o ro /dev/nvme0n1p3 /mnt/win     # use the name lsblk showed
     OLLAMA_MODELS=/mnt/win/Users/zacrh/.ollama/models OLLAMA_NOPRUNE=1 ollama serve &
     ```
     If it says the drive is BitLocker-locked or "unclean", use the other way.
   - *Download the two smaller ones* (about 11 GB, held in memory; the 32B is skipped):
     ```
     ollama serve &
     ollama pull llama3.2:latest && ollama pull qwen3:14b
     ```
7. **Run the test:**
   ```
   curl -fsSLO https://raw.githubusercontent.com/TheKingCS/MIA/master/os/poc/gpu_bench.py
   python3 gpu_bench.py
   ```
   It prints each model's load time and writing speed next to the Windows figures, whether it ran on the GPU, and
   PASS or BELOW THE BAR. It also notes what Linux sees of the Wi-Fi, Bluetooth and TPM.
8. **Keep the result:** copy `mia_gpu_bench.json` somewhere (another USB stick, or open claude.ai in Firefox and
   paste it into a chat), or photograph the screen.
9. Restart and take the stick out. Windows starts as before.

**If it says "CPU" or BELOW THE BAR:** the ROCm path didn't work well. Try once more with Ollama's other GPU
path, Vulkan (the exact switch is to be confirmed: `sudo dnf install ollama-vulkan` if Fedora offers it, then
restart `ollama serve`), and run the test again. If both fall short, the plan says test Ubuntu 26.04 the same way.

## Tests 2 to 6 on GitHub

They start by themselves when anything under `os/` changes, or by hand from the repository's Actions tab ("MIA OS
proofs of concept", Run workflow). Their results go into `docs/mia_os/MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md`.
