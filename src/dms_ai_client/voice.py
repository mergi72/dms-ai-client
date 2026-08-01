from __future__ import annotations


VOICE_JS = r"""window.DMSVoice = (() => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let listening = false;
  let speechEnabled = false;

  function initialize(input, microphoneButton, speakerButton, status) {
    if (!Recognition) {
      microphoneButton.disabled = true;
      microphoneButton.title = 'Rozpoznávání řeči není v tomto prohlížeči dostupné.';
    } else {
      recognition = new Recognition();
      recognition.lang = 'cs-CZ';
      recognition.interimResults = true;
      recognition.continuous = false;
      recognition.onstart = () => {
        listening = true;
        microphoneButton.classList.add('active');
        status.textContent = 'Poslouchám…';
      };
      recognition.onresult = event => {
        input.value = Array.from(event.results).map(result => result[0].transcript).join('');
      };
      recognition.onerror = event => {
        status.textContent = `Hlasový vstup: ${event.error}`;
        status.className = 'status error';
      };
      recognition.onend = () => {
        listening = false;
        microphoneButton.classList.remove('active');
        if (!status.classList.contains('error')) status.textContent = 'Diktování dokončeno · zkontroluj text a odešli';
        input.focus();
      };
      microphoneButton.onclick = () => listening ? recognition.stop() : recognition.start();
    }

    speakerButton.onclick = () => {
      speechEnabled = !speechEnabled;
      speakerButton.classList.toggle('active', speechEnabled);
      speakerButton.textContent = speechEnabled ? '🔊 Čtení zapnuto' : '🔇 Čtení vypnuto';
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
