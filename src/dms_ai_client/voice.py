from __future__ import annotations


VOICE_JS = r"""window.DMSVoice = (() => {
  let recorder = null;
  let stream = null;
  let chunks = [];
  let speechEnabled = false;

  function initialize(input, microphoneButton, speakerButton, status, transcribe, submit) {
    microphoneButton.textContent = '\u{1F399}\u{FE0F} Nahrát a odeslat';
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
          stream = await navigator.mediaDevices.getUserMedia({audio: true});
          const preferred = 'audio/webm;codecs=opus';
          const options = MediaRecorder.isTypeSupported(preferred) ? {mimeType: preferred} : {};
          recorder = new MediaRecorder(stream, options);
          chunks = [];
          recorder.ondataavailable = event => {
            if (event.data.size) chunks.push(event.data);
          };
          recorder.onstart = () => {
            microphoneButton.classList.add('active');
            microphoneButton.textContent = '\u23F9\u{FE0F} Zastavit a odeslat';
            status.textContent = 'Nahrávám hlas…';
            status.className = 'status';
          };
          recorder.onerror = event => {
            status.textContent = `Nahrávání selhalo: ${event.error?.message || 'neznámá chyba'}`;
            status.className = 'status error';
          };
          recorder.onstop = async () => {
            stream?.getTracks().forEach(track => track.stop());
            stream = null;
            microphoneButton.classList.remove('active');
            microphoneButton.textContent = '\u{1F399}\u{FE0F} Nahrát a odeslat';
            try {
              const audio = new Blob(chunks, {type: recorder.mimeType || 'audio/webm'});
              if (!audio.size) throw new Error('Nahrávka je prázdná.');
              status.textContent = 'Přepisuji hlas…';
              input.value = await transcribe(audio);
              if (!input.value.trim()) throw new Error('V nahrávce nebyla rozpoznána řeč.');
              await submit();
            } catch (error) {
              status.textContent = String(error);
              status.className = 'status error';
              input.focus();
            } finally {
              chunks = [];
              microphoneButton.disabled = false;
            }
          };
          recorder.start();
        } catch (error) {
          stream?.getTracks().forEach(track => track.stop());
          stream = null;
          status.textContent = `Mikrofon: ${error.message || error}`;
          status.className = 'status error';
        }
      };
    }

    speakerButton.onclick = () => {
      speechEnabled = !speechEnabled;
      speakerButton.classList.toggle('active', speechEnabled);
      speakerButton.textContent = speechEnabled ? '\u{1F50A} Čtení zapnuto' : '\u{1F507} Čtení vypnuto';
      if (!speechEnabled) window.speechSynthesis.cancel();
    };
  }

  function speak(text) {
    if (!speechEnabled || !window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'cs-CZ';
    window.speechSynthesis.speak(utterance);
  }

  return {initialize, speak};
})();"""
