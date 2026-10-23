(() => {
  // Authenticated Passive HDMI / Wireless Display Viewer for OpenDeskCast
  // Supports direct QR token (?t=...) OR 4-digit PIN entry on http://opendeskcast.local:8765
  const canvas = document.getElementById("viewer-canvas");
  const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
  const pinOverlay = document.getElementById("pin-overlay");
  const pinBoxes = document.getElementById("pin-boxes");
  const digitEls = [
    document.getElementById("pin-d0"),
    document.getElementById("pin-d1"),
    document.getElementById("pin-d2"),
    document.getElementById("pin-d3"),
  ];

  const params = new URLSearchParams(window.location.search);
  let sessionToken = params.get("t") || "";

  // Strip the token from the visible URL / browser history so refreshing after session end requires new auth
  try {
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", "/");
    }
  } catch (_) {}

  let wsStream = null;
  let wsAudio = null;
  let audioCtx = null;
  let nextAudioTime = 0;
  let rendering = false;
  let pendingBuffer = null;
  let reconnectTimer = null;
  let sessionTerminated = false;
  let enteredPin = "";
  let verifyingPin = false;
  let audioUnlocked = false;

  async function processPendingFrames() {
    if (rendering) return;
    rendering = true;
    try {
      while (pendingBuffer !== null && !sessionTerminated) {
        const buf = pendingBuffer;
        pendingBuffer = null;

        const hdr = new DataView(buf, 0, 8);
        const fullW = hdr.getUint16(0, true);
        const fullH = hdr.getUint16(2, true);
        const patchX = hdr.getUint16(4, true);
        const patchY = hdr.getUint16(6, true);

        const jpegSlice = new Uint8Array(buf, 8);
        const blob = new Blob([jpegSlice], { type: "image/jpeg" });
        let bmp;
        try {
          bmp = await createImageBitmap(blob, {
            premultiplyAlpha: "none",
            colorSpaceConversion: "none",
          });
        } catch (_) {
          bmp = await createImageBitmap(blob);
        }

        if (fullW > 0 && fullH > 0 && (canvas.width !== fullW || canvas.height !== fullH)) {
          canvas.width = fullW;
          canvas.height = fullH;
          ctx.imageSmoothingEnabled = false;
        }
        ctx.drawImage(bmp, patchX, patchY);
        bmp.close();

        if (wsStream && wsStream.readyState === WebSocket.OPEN) {
          try {
            wsStream.send("1");
          } catch (_) {}
        }
      }
    } catch (_) {
    } finally {
      rendering = false;
      if (pendingBuffer !== null && !sessionTerminated) {
        processPendingFrames();
      }
    }
  }

  function wipeToBlackAndLock() {
    sessionTerminated = true;
    sessionToken = "";
    if (pinOverlay) pinOverlay.classList.add("hidden");
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (wsAudio) {
      try {
        wsAudio.close();
      } catch (_) {}
      wsAudio = null;
    }
    if (audioCtx) {
      try {
        audioCtx.close();
      } catch (_) {}
      audioCtx = null;
    }
    nextAudioTime = 0;
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, canvas.width || 1920, canvas.height || 1080);
  }

  function renderPinDigits() {
    for (let i = 0; i < 4; i++) {
      if (!digitEls[i]) continue;
      digitEls[i].textContent = enteredPin[i] || "";
      digitEls[i].classList.toggle("filled", i < enteredPin.length);
    }
  }

  async function submitPin(pinCode) {
    if (verifyingPin) return;
    verifyingPin = true;
    try {
      const res = await fetch("/api/verify-pin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: pinCode }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data && data.token) {
          sessionToken = data.token;
          sessionTerminated = false;
          if (pinOverlay) pinOverlay.classList.add("hidden");
          requestWakeLockAndFullscreen();
          connectStream();
          verifyingPin = false;
          return;
        }
      }
    } catch (_) {}

    if (pinBoxes) pinBoxes.classList.add("pin-error");
    setTimeout(() => {
      if (pinBoxes) pinBoxes.classList.remove("pin-error");
      enteredPin = "";
      renderPinDigits();
      verifyingPin = false;
    }, 420);
  }

  function handlePinKey(key) {
    ensureAudioUnlocked();
    if (verifyingPin || sessionToken) return;
    if (key === "C") {
      enteredPin = "";
      renderPinDigits();
      return;
    }
    if (key === "B") {
      enteredPin = enteredPin.slice(0, -1);
      renderPinDigits();
      return;
    }
    if (/^[0-9]$/.test(key) && enteredPin.length < 4) {
      enteredPin += key;
      renderPinDigits();
      if (enteredPin.length === 4) {
        submitPin(enteredPin);
      }
    }
  }

  if (pinOverlay) {
    pinOverlay.querySelectorAll(".pin-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const k = btn.getAttribute("data-k");
        if (k) handlePinKey(k);
      });
    });
  }

  window.addEventListener("keydown", (e) => {
    if (!pinOverlay || pinOverlay.classList.contains("hidden")) return;
    if (e.key >= "0" && e.key <= "9") {
      handlePinKey(e.key);
    } else if (e.key === "Backspace") {
      handlePinKey("B");
    } else if (e.key === "Escape" || e.key === "Delete") {
      handlePinKey("C");
    }
  });

  // 1-sample silent WAV data URI to unlock iOS / iPadOS WebKit AVAudioSession
  const SILENT_WAV = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
  let unlockAudioEl = null;

  function initAudioContext() {
    if (audioCtx) return;
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    try {
      audioCtx = new AudioContextClass({ latencyHint: "interactive" });
    } catch (_) {
      try {
        audioCtx = new AudioContextClass();
      } catch (_) {}
    }
  }

  function requestScreenWakeLock() {
    try {
      if ("wakeLock" in navigator && !sessionTerminated) {
        navigator.wakeLock.request("screen").catch(() => {});
      }
    } catch (_) {}
  }

  function ensureAudioUnlocked() {
    initAudioContext();
    requestScreenWakeLock();
    if (!unlockAudioEl) {
      try {
        unlockAudioEl = document.createElement("audio");
        unlockAudioEl.src = SILENT_WAV;
        unlockAudioEl.setAttribute("playsinline", "true");
        unlockAudioEl.setAttribute("webkit-playsinline", "true");
      } catch (_) {}
    }
    if (unlockAudioEl) {
      try {
        unlockAudioEl.play().catch(() => {});
      } catch (_) {}
    }

    if (audioCtx) {
      try {
        // iOS/WebKit hardware output unlock via silent buffer
        const dummy = audioCtx.createBuffer(1, 1, 22050);
        const src = audioCtx.createBufferSource();
        src.buffer = dummy;
        src.connect(audioCtx.destination);
        src.start(0);
      } catch (_) {}

      if (audioCtx.state === "suspended" || audioCtx.state === "interrupted") {
        audioCtx.resume().then(() => {
          if (audioCtx.state === "running") {
            audioUnlocked = true;
          }
        }).catch(() => {});
      } else if (audioCtx.state === "running") {
        audioUnlocked = true;
      }
    }
  }

  function toggleFullscreen() {
    try {
      if (!document.fullscreenElement) {
        if (document.documentElement.requestFullscreen) {
          document.documentElement.requestFullscreen().catch(() => {});
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen().catch(() => {});
        }
      }
    } catch (_) {}
  }

  let lastTapTime = 0;
  function handleTapInteraction() {
    ensureAudioUnlocked();
    const now = Date.now();
    if (now - lastTapTime < 320) {
      toggleFullscreen();
      lastTapTime = 0;
    } else {
      lastTapTime = now;
    }
  }

  window.addEventListener("pointerdown", ensureAudioUnlocked, { passive: true });
  window.addEventListener("touchstart", ensureAudioUnlocked, { passive: true });
  window.addEventListener("touchend", handleTapInteraction, { passive: true });
  window.addEventListener("click", handleTapInteraction);
  window.addEventListener("keydown", ensureAudioUnlocked);

  function connectAudio() {
    if (sessionTerminated || !sessionToken) return;
    if (wsAudio && wsAudio.readyState <= WebSocket.OPEN) return;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    wsAudio = new WebSocket(
      `${proto}//${window.location.host}/ws/audio?t=${encodeURIComponent(sessionToken)}`
    );
    wsAudio.binaryType = "arraybuffer";

    wsAudio.onopen = () => {
      initAudioContext();
      if (audioCtx) {
        if (audioCtx.state === "suspended" || audioCtx.state === "interrupted") {
          audioCtx.resume().then(() => {
            if (audioCtx.state === "running") {
              audioUnlocked = true;
            }
          }).catch(() => {});
        } else if (audioCtx.state === "running") {
          audioUnlocked = true;
        }
      }
    };

    wsAudio.onmessage = (ev) => {
      if (!(ev.data instanceof ArrayBuffer)) return;
      if (!audioCtx) {
        initAudioContext();
      }
      if (!audioCtx) return;

      if (audioCtx.state === "suspended" || audioCtx.state === "interrupted") {
        audioCtx.resume().then(() => {
          if (audioCtx.state === "running") {
            audioUnlocked = true;
          }
        }).catch(() => {});
        return;
      }

      const int16 = new Int16Array(ev.data);
      if (int16.length === 0) return;
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768.0;
      }

      let buf;
      try {
        buf = audioCtx.createBuffer(1, float32.length, 48000);
      } catch (_) {
        try {
          buf = audioCtx.createBuffer(1, float32.length, audioCtx.sampleRate || 44100);
        } catch (_) {
          return;
        }
      }
      buf.getChannelData(0).set(float32);
      const src = audioCtx.createBufferSource();
      src.buffer = buf;
      src.connect(audioCtx.destination);

      const now = audioCtx.currentTime;
      if (nextAudioTime < now || nextAudioTime > now + 0.25) {
        nextAudioTime = now + 0.03;
      }
      src.start(nextAudioTime);
      nextAudioTime += buf.duration;
    };

    wsAudio.onclose = () => {
      wsAudio = null;
      if (!sessionTerminated && sessionToken) {
        setTimeout(connectAudio, 800);
      }
    };

    wsAudio.onerror = () => {
      try {
        wsAudio.close();
      } catch (_) {}
    };
  }

  function scheduleReconnect(delayMs = 400) {
    if (sessionTerminated || !sessionToken) return;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connectStream, delayMs);
  }

  function connectStream() {
    if (sessionTerminated || !sessionToken) {
      wipeToBlackAndLock();
      return;
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (wsStream) {
      try {
        wsStream.onclose = null;
        wsStream.close();
      } catch (_) {}
    }

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    wsStream = new WebSocket(
      `${proto}//${window.location.host}/ws/stream?t=${encodeURIComponent(sessionToken)}`
    );
    wsStream.binaryType = "arraybuffer";

    wsStream.onopen = () => {
      connectAudio();
    };

    wsStream.onmessage = (ev) => {
      if (sessionTerminated || !(ev.data instanceof ArrayBuffer) || ev.data.byteLength <= 8) return;
      pendingBuffer = ev.data;
      if (!rendering) {
        processPendingFrames();
      }
    };

    wsStream.onclose = (ev) => {
      // 4000 = PC closed OpenDeskCast or rotated token; 4003 = invalid/expired token or locked session
      if (ev.code === 4000 || ev.code === 4003 || ev.code === 1000) {
        wipeToBlackAndLock();
        return;
      }
      scheduleReconnect(400);
    };

    wsStream.onerror = () => {
      try {
        wsStream.close();
      } catch (_) {}
    };
  }

  if (sessionToken) {
    connectStream();
  } else if (pinOverlay) {
    pinOverlay.classList.remove("hidden");
  }
})();
