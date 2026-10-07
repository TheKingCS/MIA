#!/usr/bin/env bash
# llama.cpp's server for MIA's own model on the phone (DEC-0019,
# docs/PHONE_MODEL_TEST.md), built with Android's NDK for the phone
# (arm64-v8a) and the CI emulator (x86_64). It goes into the app as
# jniLibs/<abi>/libllama_server.so: Android only lets an app run programs
# from its native library folder, and only files named lib*.so land there.
# Usage: ANDROID_NDK=/path/to/ndk bash android-phone/build_llama_server.sh
set -euo pipefail
TAG=b11467  # the llama.cpp release this build is pinned to
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-$HERE/build/llama.cpp}
NDK=${ANDROID_NDK:?set ANDROID_NDK to the Android NDK folder}
if [ ! -d "$WORK/.git" ]; then
  git clone -q --depth 1 --branch "$TAG" https://github.com/ggml-org/llama.cpp "$WORK"
fi
for ABI in arm64-v8a x86_64; do
  # Phones: Armv8.2 with dot product and half floats (every phone chip since
  # about 2019, the Galaxy A54's Exynos 1380 among them). Emulator: plain x86-64.
  if [ "$ABI" = arm64-v8a ]; then FLAGS="-march=armv8.2-a+dotprod+fp16"; else FLAGS="-march=x86-64-v2"; fi
  cmake -S "$WORK" -B "$WORK/build-$ABI" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI="$ABI" -DANDROID_PLATFORM=android-26 -DANDROID_STL=c++_static \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="$FLAGS" -DCMAKE_CXX_FLAGS="$FLAGS" \
    -DGGML_NATIVE=OFF -DGGML_OPENMP=OFF -DGGML_LLAMAFILE=OFF -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF \
    -DBUILD_SHARED_LIBS=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON
  cmake --build "$WORK/build-$ABI" --target llama-server -j "$(nproc)"
  mkdir -p "$HERE/app/src/main/jniLibs/$ABI"
  cp "$WORK/build-$ABI/bin/llama-server" "$HERE/app/src/main/jniLibs/$ABI/libllama_server.so"
  "$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip" "$HERE/app/src/main/jniLibs/$ABI/libllama_server.so"
  ls -la "$HERE/app/src/main/jniLibs/$ABI/libllama_server.so"
done
