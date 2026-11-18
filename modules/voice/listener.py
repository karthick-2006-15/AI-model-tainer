"""
JARVIS Always-On Voice & Wake-Word Listening Service
Runs a resilient background daemon that continuously captures microphone audio,
detects the "Hey Jarvis" wake-phrase or maintains continuous multi-turn conversations,
supports Tanglish/Hinglish/English, executes commands, and vocalizes responses.
"""

import threading
import logging
import time
import asyncio
from typing import Optional, Callable
import speech_recognition as sr
from modules.voice.wakeword import wakeword_detector
from modules.voice.tts import tts_engine
from modules.voice.multilingual import multilingual_engine
from modules.voice.conversation import conversation_manager
from modules.voice.state_machine import voice_state_machine, VoiceState
from core.brain.orchestrator import brain_orchestrator
from modules.computer_use.whatsapp import whatsapp_automation

logger = logging.getLogger("jarvis.voice.listener")


class VoiceListener:
    def __init__(self, language: str = "en-US"):
        self.language = language
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = 250
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.6
        self._recognizer.non_speaking_duration = 0.35
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
        """Main listening loop with multi-turn support, language detection, and noise calibration."""
        logger.info("Initializing microphone input device...")
        
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
                            # Listen for speech phrase
                            voice_state_machine.transition_to(VoiceState.IDLE, "Waiting for wake phrase or speech")
                            audio = self._recognizer.listen(
                                source,
                                timeout=None,
                                phrase_time_limit=7
                            )
                            voice_state_machine.transition_to(VoiceState.PROCESSING, "Transcribing speech")

                            transcript = ""
                            try:
                                transcript = self._recognizer.recognize_google(audio, language=self.language)
                            except sr.UnknownValueError:
                                voice_state_machine.transition_to(VoiceState.IDLE)
                                continue
                            except sr.RequestError as e:
                                logger.warning(f"Google STT service temporarily unreachable: {e}")
                                voice_state_machine.transition_to(VoiceState.ERROR, f"STT unreachable: {e}")
                                time.sleep(1.0)
                                continue

                            if not transcript:
                                voice_state_machine.transition_to(VoiceState.IDLE)
                                continue

                            logger.info(f"Heard audio transcript: '{transcript}'")

                            # Process speech through Conversation Manager (handles continuous mode & confirmations)
                            conv_res = conversation_manager.process_incoming_speech(transcript)

                            # Case A: User answered a pending confirmation challenge ("Yes", "Aama", "Haan", "No")
                            if conv_res.get("is_confirmation_response"):
                                approved = conv_res["approved"]
                                lang = conv_res.get("language", "en")
                                pending = conv_res.get("pending_action") or {}

                                if approved:
                                    logger.info(f"User confirmed pending action: {pending.get('action')}")
                                    # Execute authorized action
                                    if pending.get("action") == "whatsapp_send":
                                        recip = pending.get("recipient")
                                        msg = pending.get("message")
                                        send_res = whatsapp_automation.send_message(
                                            recipient=recip,
                                            message_text=msg,
                                            skip_permission_check=True
                                        )
                                        reply = "Message sent successfully." if send_res.get("success") else "Failed to send message."
                                    elif pending.get("action") == "worksheet_submit":
                                        from modules.computer_use.worksheet import worksheet_engine
                                        sub_res = worksheet_engine.submit_worksheet(skip_permission_check=True)
                                        reply = "Worksheet submitted successfully." if sub_res.get("success") else "Submission failed."
                                    else:
                                        reply = "Action confirmed and executed."

                                    localized_reply = multilingual_engine.localize_response(reply, lang)
                                    tts_engine.speak(localized_reply)
                                    self._notify_callbacks(transcript, localized_reply)
                                else:
                                    logger.info("User denied pending action.")
                                    cancel_reply = multilingual_engine.localize_response("Action cancelled.", lang)
                                    tts_engine.speak(cancel_reply)
                                    self._notify_callbacks(transcript, cancel_reply)
                                continue

                            # Case B: Unrelated background speech while idle
                            if not conv_res.get("handled"):
                                continue

                            lang = conv_res.get("language", "en")

                            # Case C: User said greeting / wake-word only ("Hey Jarvis")
                            if conv_res.get("is_greeting_only"):
                                greeting_resp = multilingual_engine.localize_response("Yes, I'm listening.", lang)
                                tts_engine.speak(greeting_resp)
                                self._notify_callbacks(transcript, greeting_resp)
                                continue

                            # Case D: Actionable instruction (either via wake-word or continuous turn)
                            cmd = conv_res.get("canonical_instruction") or transcript
                            self._execute_and_reply(cmd, lang=lang, original_query=transcript)

                        except sr.WaitTimeoutError:
                            continue
                        except Exception as e:
                            logger.warning(f"Listening loop inner warning: {e}")
                            time.sleep(0.4)

            except Exception as e:
                logger.error(f"Microphone device error: {e}. Retrying in 2 seconds...")
                time.sleep(2.0)

    def _execute_and_reply(self, command_text: str, lang: str = "en", original_query: str = ""):
        """Dispatches command to Brain Orchestrator, formats concise reply, and vocalizes in user's language."""
        try:
            logger.info(f"Dispatching voice command: '{command_text}' (lang={lang})")
            voice_state_machine.transition_to(VoiceState.THINKING, f"Analyzing: {command_text}")
            if not self._event_loop:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)

            result = self._event_loop.run_until_complete(
                brain_orchestrator.process_user_request(command_text)
            )

            raw_response = result.get("response", "Action completed, sir.")
            tool_name = result.get("tool_executed")

            # Check if this action prepared a Level 3 confirmation (e.g. WhatsApp draft or worksheet review)
            requires_conf = False
            action_details = None

            if "whatsapp" in str(tool_name).lower() and ("send" in command_text.lower() or "prepare" in str(tool_name).lower()):
                # Check WhatsApp draft
                draft = getattr(whatsapp_automation, "_last_prepared_draft", None)
                if draft and draft.get("status") == "awaiting_user_confirmation":
                    requires_conf = True
                    action_details = {
                        "action": "whatsapp_send",
                        "recipient": draft.get("recipient"),
                        "message": draft.get("message")
                    }

            conversation_manager.record_assistant_response(
                response_text=raw_response,
                requires_confirmation=requires_conf,
                action_details=action_details
            )

            # Localize response to match user's language (Tamil, Tanglish, Hindi, Hinglish, English)
            localized_response = multilingual_engine.localize_response(raw_response, lang)

            # Vocalize response
            voice_state_machine.transition_to(VoiceState.SPEAKING, "Vocalizing response")
            tts_engine.speak(localized_response)

            # Broadcast to HUD
            self._notify_callbacks(original_query or command_text, localized_response)
            voice_state_machine.transition_to(VoiceState.IDLE, "Standing by")

        except Exception as e:
            logger.error(f"Error executing voice command: {e}")
            voice_state_machine.transition_to(VoiceState.ERROR, str(e))
            err_msg = multilingual_engine.localize_response("I encountered an error executing that request, sir.", lang)
            tts_engine.speak(err_msg)

    def _notify_callbacks(self, command_text: str, response_text: str):
        for cb in self.on_command_callbacks:
            try:
                cb(command_text, response_text)
            except Exception as ex_cb:
                logger.warning(f"Callback error: {ex_cb}")


# Global singleton instance
voice_listener = VoiceListener()
