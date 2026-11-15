"""
JARVIS Always-On Voice & Wake-Word Listening Service
Runs a resilient background daemon that continuously captures microphone audio,
detects the "Hey Jarvis" wake-phrase, executes commands via the Brain Orchestrator,
and vocalizes responses immediately through the system speakers.
"""

import threading
import logging
import time
import asyncio
from typing import Optional, Callable
import speech_recognition as sr
from modules.voice.wakeword import wakeword_detector
from modules.voice.tts import tts_engine
from core.brain.orchestrator import brain_orchestrator

logger = logging.getLogger("jarvis.voice.listener")


class VoiceListener:
    def __init__(self, language: str = "en-US"):
        self.language = language
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = 250
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.8
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.on_command_callbacks = []

    def register_command_callback(self, callback: Callable[[str, str], None]):
        """Registers callback(command_text, response_text) for UI/WebSocket broadcasts."""
        self.on_command_callbacks.append(callback)

    def is_active(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def start(self):
        """Starts the continuous microphone listener on a background daemon thread."""
        if self._running:
            logger.info("VoiceListener is already running.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="JARVIS_Voice_Listener")
        self._thread.start()
        logger.info("JARVIS Always-On Voice Listener started successfully.")

    def stop(self):
        """Stops the voice listener."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("JARVIS Voice Listener stopped.")

    def _listen_loop(self):
        """Main listening loop with auto-recovery and noise calibration."""
        logger.info("Initializing microphone input device...")
        
        # Create an asyncio event loop for this thread if needed
        try:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
        except Exception:
            pass

        while self._running:
            try:
                with sr.Microphone() as source:
                    logger.info("Calibrating microphone for ambient noise...")
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    logger.info(f"Microphone ready. Energy threshold: {self._recognizer.energy_threshold:.1f}")

                    while self._running:
                        try:
                            # Listen for speech phrase (non-blocking chunk)
                            audio = self._recognizer.listen(
                                source,
                                timeout=None,
                                phrase_time_limit=6
                            )

                            # Transcribe captured phrase
                            transcript = ""
                            try:
                                transcript = self._recognizer.recognize_google(audio, language=self.language)
                            except sr.UnknownValueError:
                                # Silence or unintelligible room audio
                                continue
                            except sr.RequestError as e:
                                logger.warning(f"Google STT service temporarily unreachable: {e}")
                                time.sleep(1.0)
                                continue

                            if not transcript:
                                continue

                            logger.info(f"Heard audio transcript: '{transcript}'")

                            # Check for Wake Word ("Hey Jarvis")
                            wake_detected, command = wakeword_detector.check_text(transcript)

                            if wake_detected:
                                if command:
                                    logger.info(f"Wake word detected with direct command: '{command}'")
                                    self._execute_and_reply(command)
                                else:
                                    # User said "Hey Jarvis" alone -> Acknowledge and prompt for command
                                    logger.info("Wake word detected without command. Prompting user...")
                                    tts_engine.speak("Yes sir, I am listening.")
                                    time.sleep(0.4)

                                    try:
                                        # Prompt listen mode for immediate follow-up
                                        follow_up_audio = self._recognizer.listen(
                                            source,
                                            timeout=5.0,
                                            phrase_time_limit=8.0
                                        )
                                        follow_up_cmd = self._recognizer.recognize_google(
                                            follow_up_audio,
                                            language=self.language
                                        )
                                        if follow_up_cmd:
                                            logger.info(f"Follow-up command received: '{follow_up_cmd}'")
                                            self._execute_and_reply(follow_up_cmd)
                                        else:
                                            tts_engine.speak("Standing by, sir.")
                                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                                        tts_engine.speak("Standing by, sir.")
                                    except Exception as ex_prompt:
                                        logger.warning(f"Error in prompt listening: {ex_prompt}")

                        except sr.WaitTimeoutError:
                            continue
                        except Exception as e:
                            logger.warning(f"Listening loop inner warning: {e}")
                            time.sleep(0.5)

            except Exception as e:
                logger.error(f"Microphone device error: {e}. Retrying in 2 seconds...")
                time.sleep(2.0)

    def _execute_and_reply(self, command_text: str):
        """Dispatches command to Brain Orchestrator and speaks response aloud."""
        try:
            logger.info(f"Dispatching voice command to Brain Orchestrator: '{command_text}'")
            if not self._event_loop:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)

            result = self._event_loop.run_until_complete(
                brain_orchestrator.process_user_request(command_text)
            )

            response_text = result.get("response", "Command executed, sir.")
            logger.info(f"Brain response: '{response_text}'")

            # Vocalize response out loud immediately
            tts_engine.speak(response_text)

            # Notify any registered UI callbacks
            for cb in self.on_command_callbacks:
                try:
                    cb(command_text, response_text)
                except Exception as ex_cb:
                    logger.warning(f"Callback error: {ex_cb}")

        except Exception as e:
            logger.error(f"Error executing voice command: {e}")
            tts_engine.speak("I encountered an error executing that request, sir.")


# Global singleton instance
voice_listener = VoiceListener()
