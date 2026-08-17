from __future__ import annotations


VOICE_JS = r"""window.DMSVoice = (() => {
  let recorder = null;
  let stream = null;
  let chunks = [];
  let recordingStartedAt = 0;
  let speechEnabled = false;
  let preferredVoiceName = '';
  let recordingUrl = '';
  let warmupTimer = null;

  const microphoneConstraints = {
    channelCount: {ideal: 1},
    sampleRate: {ideal: 48000},
    echoCancellation: {ideal: false},
    noiseSuppression: {ideal: false},
    autoGainControl: {ideal: false},
  };

  function selectCzechFemaleVoice() {
    const voices = window.speechSynthesis?.getVoices() || [];
    const czechVoices = voices.filter(voice => voice.lang?.toLowerCase().startsWith('cs'));
    const preferred = preferredVoiceName.toLowerCase();
    const configuredVoice = czechVoices.find(
      voice => preferred && voice.name.toLowerCase().includes(preferred)
    );
    if (preferred) return configuredVoice || null;
    return czechVoices.find(voice => /vlasta|zuzana|tereza|female|woman|žena/i.test(voice.name)) || null;
  }

  function initialize(input, microphoneButton, playbackButton, speakerButton, status, transcribe, configuredVoice) {
    preferredVoiceName = configuredVoice || '';
    microphoneButton.textContent = '\u{1F399}\u{FE0F} Nadiktovat';
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      microphoneButton.disabled = true;
      microphoneButton.title = 'Nahrávání zvuku není v tomto prohlížeči dostupné.';
    } else {
      microphoneButton.onclick = async () => {
        if (recorder?.state === 'recording') {
          microphoneButton.disabled = true;
          recorder.stop();
          return;
        }
        try {
          stream = await navigator.mediaDevices.getUserMedia({audio: microphoneConstraints});
          const track = stream.getAudioTracks()[0];
          const microphoneName = track?.label || 'výchozí mikrofon';
          const preferred = 'audio/webm;codecs=opus';
          const options = {audioBitsPerSecond: 128000};
          if (MediaRecorder.isTypeSupported(preferred)) options.mimeType = preferred;
          recorder = new MediaRecorder(stream, options);
          chunks = [];
          recorder.ondataavailable = event => {
            if (event.data.size) chunks.push(event.data);
          };
          recorder.onstart = () => {
            if (recordingUrl) URL.revokeObjectURL(recordingUrl);
            recordingUrl = '';
            playbackButton.hidden = true;
            recordingStartedAt = performance.now();
            microphoneButton.classList.add('active');
            microphoneButton.textContent = '\u23F9\u{FE0F} Zastavit';
            microphoneButton.disabled = true;
            status.textContent = `Připravuji mikrofon… ${microphoneName}`;
            status.className = 'status';
            warmupTimer = setTimeout(() => {
              warmupTimer = null;
              microphoneButton.disabled = false;
              status.textContent = `Mluvte · ${microphoneName}`;
            }, 1000);
          };
          recorder.onerror = event => {
            status.textContent = `Nahrávání selhalo: ${event.error?.message || 'neznámá chyba'}`;
            status.className = 'status error';
          };
          recorder.onstop = async () => {
            if (warmupTimer) clearTimeout(warmupTimer);
            warmupTimer = null;
            const durationSeconds = Math.max(0, (performance.now() - recordingStartedAt) / 1000);
            stream?.getTracks().forEach(track => track.stop());
            stream = null;
            microphoneButton.classList.remove('active');
            microphoneButton.textContent = '\u{1F399}\u{FE0F} Nadiktovat';
            try {
              const audio = new Blob(chunks, {type: recorder.mimeType || 'audio/webm'});
              if (!audio.size) throw new Error('Nahrávka je prázdná.');
              if (durationSeconds < 0.8) throw new Error('Nahrávka je příliš krátká. Mluvte alespoň jednu sekundu.');
              recordingUrl = URL.createObjectURL(audio);
              playbackButton.hidden = false;
              playbackButton.onclick = () => new Audio(recordingUrl).play();
              playbackButton.title = `${durationSeconds.toFixed(1)} s · ${microphoneName}`;
              status.textContent = `Přepisuji ${durationSeconds.toFixed(1)} s hlasu…`;
              input.value = await transcribe(audio);
              if (!input.value.trim()) {
                input.value = '';
                status.textContent = 'Připraveno';
                status.className = 'status';
                input.focus();
                return;
              }
              input.dataset.source = 'voice';
              status.textContent = 'Přepis je připravený ke kontrole a odeslání.';
              status.className = 'status';
              input.focus();
            } catch (error) {
              status.textContent = String(error);
              status.className = 'status error';
              input.focus();
            } finally {
              chunks = [];
              microphoneButton.disabled = false;
            }
          };
          recorder.start(250);
        } catch (error) {
          stream?.getTracks().forEach(track => track.stop());
          stream = null;
          status.textContent = `Mikrofon: ${error.message || error}`;
          status.className = 'status error';
        }
      };
    }

    speakerButton.onclick = () => {
      const voice = selectCzechFemaleVoice();
      if (!speechEnabled && !voice) {
        speechEnabled = false;
        speakerButton.classList.remove('active');
        speakerButton.textContent = '\u{1F507} Čtení vypnuto';
        status.textContent = preferredVoiceName
          ? `Hlas ${preferredVoiceName} není v tomto prohlížeči dostupný.`
          : 'Český ženský hlas nebyl v tomto prohlížeči nalezen.';
        status.className = 'status error';
        return;
      }
      speechEnabled = !speechEnabled;
      speakerButton.classList.toggle('active', speechEnabled);
      speakerButton.textContent = speechEnabled ? '\u{1F50A} Čtení zapnuto' : '\u{1F507} Čtení vypnuto';
      speakerButton.title = voice ? `Hlas: ${voice.name}` : 'Český hlas nebyl nalezen.';
      status.textContent = speechEnabled && voice ? `Čtení hlasem: ${voice.name}` : 'Připraveno';
      status.className = 'status';
      if (!speechEnabled) window.speechSynthesis.cancel();
    };
  }

  function speak(text) {
    if (!speechEnabled || !window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'cs-CZ';
    const voice = selectCzechFemaleVoice();
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
  }

  return {initialize, speak};
})();"""
