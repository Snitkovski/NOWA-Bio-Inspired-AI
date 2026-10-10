"""
Audio system for Chinchilla Agent.
Plays sound effects for interactions and behaviors.
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import random

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


# ============================================================================
# AUDIO SYSTEM
# ============================================================================

class AudioSystem:
    """
    Manages sound effects for interactions and behaviors.
    Maps interaction types to appropriate audio files.
    """
    
    # Sound effect mappings for interactions
    INTERACTION_SOUNDS = {
        "pet_head": ["squeak_soft.wav", "chirp.wav", "fur_rustle.wav"],
        "pet_back": ["fur_rustle.wav", "squeak_soft.wav"],
        "feed": ["chewing.wav", "chewing_soft.wav"],
        "play": ["toy_rattle.wav", "jump_land.wav", "steps_fast.wav"],
        "scare": ["alarm_call.wav", "scratch_bars.wav", "squeak_soft.wav"],
    }
    
    # Sound effects for behaviors
    BEHAVIOR_SOUNDS = {
        "activity_burst": ["steps_fast.wav", "jump_land.wav", "wheel_spin.wav"],
        "eating_and_grooming": ["chewing.wav", "gnawing.wav"],
        "full_grooming": ["fur_rustle.wav", "scratch_bars.wav"],
        "dust_bathing": ["rustling.wav", "steps_soft.wav"],
        "bedtime_routine": ["steps_soft.wav", "fur_rustle.wav"],
        "rest_loaf": [],  # Quiet rest
        "extreme_fear": ["alarm_call.wav", "scratch_bars.wav"],
        "chronic_stress": ["thump_soft.wav"],
        "freezing": [],  # Silent fear
    }
    
    def __init__(self, sfx_dir: Path, logger: Optional[logging.Logger] = None):
        """
        Initialize audio system.
        
        Args:
            sfx_dir: Path to sound effects directory
            logger: Optional logger
        """
        self.logger = logger or logging.getLogger(__name__)
        self.sfx_dir = Path(sfx_dir)
        self.sounds: Dict[str, Optional['pygame.mixer.Sound']] = {}
        self.enabled = PYGAME_AVAILABLE
        self.backend = None
        
        if not self.enabled:
            # try Windows winsound fallback if pygame not available
            try:
                import winsound
                self.backend = "winsound"
                self.enabled = True
                self.logger.info("Using winsound fallback for audio")
            except ImportError:
                self.logger.warning("Pygame mixer not available, audio disabled")
                self.enabled = False
                return
        else:
            self.backend = "pygame"
        
        # Initialize pygame mixer if using pygame backend
        if self.backend == "pygame":
            try:
                pygame.mixer.init()
                self._preload_sounds()
                self.logger.info(f"Audio system initialized with {len(self.sounds)} sounds")
            except Exception as e:
                self.logger.error(f"Failed to initialize audio: {e}")
                self.enabled = False
    
    def _preload_sounds(self) -> None:
        """Preload all sound effects into memory."""
        all_sounds = set()
        
        # Collect all sound files
        for sounds_list in self.INTERACTION_SOUNDS.values():
            all_sounds.update(sounds_list)
        for sounds_list in self.BEHAVIOR_SOUNDS.values():
            all_sounds.update(sounds_list)
        
        # Load sounds
        for sound_file in all_sounds:
            try:
                sound_path = self.sfx_dir / sound_file
                if sound_path.exists():
                    self.sounds[sound_file] = pygame.mixer.Sound(str(sound_path))
                else:
                    self.logger.warning(f"Sound file not found: {sound_path}")
                    self.sounds[sound_file] = None
            except Exception as e:
                self.logger.warning(f"Failed to load sound {sound_file}: {e}")
                self.sounds[sound_file] = None
    
    def play_interaction_sound(self, interaction_type: str) -> None:
        """
        Play sound effect for an interaction.
        
        Args:
            interaction_type: Type of interaction (pet, feed, play, scare)
        """
        if not self.enabled or interaction_type not in self.INTERACTION_SOUNDS:
            return
        
        if not PYGAME_AVAILABLE:
            return
        
        sound_files = self.INTERACTION_SOUNDS.get(interaction_type, [])
        if not sound_files:
            return
        
        # Pick a random sound from the list
        sound_file = random.choice(sound_files)
        self.play_sound(sound_file)
    
    def play_behavior_sound(self, chain_name: Optional[str]) -> None:
        """
        Play sound effect for a behavior chain.
        
        Args:
            chain_name: Name of the behavioral chain
        """
        if not self.enabled or not chain_name:
            return
        
        if not PYGAME_AVAILABLE:
            return
        
        sound_files = self.BEHAVIOR_SOUNDS.get(chain_name, [])
        if not sound_files:
            return
        
        # Play occasional sounds (not every tick)
        import random
        if random.random() > 0.9:  # 10% chance per update
            sound_file = random.choice(sound_files)
            self.play_sound(sound_file)
    
    def play_sound(self, sound_file: str) -> None:
        """
        Play a specific sound file.
        
        Args:
            sound_file: Filename of sound to play (relative to sfx_dir)
        """
        if not self.enabled:
            return

        # winsound fallback simply plays file path if available
        if self.backend == "winsound":
            try:
                import winsound
                # Skip non-wav files for winsound
                if not sound_file.lower().endswith('.wav'):
                    self.logger.debug(f"winsound: skipping non-wav {sound_file}")
                    return
                path = str((self.sfx_dir / sound_file).resolve())
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                self.logger.debug(f"winsound failed to play {sound_file}: {e}")
            return

        # otherwise pygame backend
        if not PYGAME_AVAILABLE:
            return
        
        sound = self.sounds.get(sound_file)
        if sound:
            try:
                sound.play()
            except Exception as e:
                self.logger.debug(f"Failed to play sound {sound_file}: {e}")

    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable audio output at runtime.
        Disabling stops currently playing channels.
        """
        enabled = bool(enabled)
        if not PYGAME_AVAILABLE:
            self.enabled = False
            return

        if not enabled:
            try:
                pygame.mixer.stop()
            except Exception:
                pass

        self.enabled = enabled
    
    def cleanup(self) -> None:
        """Clean up audio resources."""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
            except Exception as e:
                self.logger.debug(f"Error during audio cleanup: {e}")
