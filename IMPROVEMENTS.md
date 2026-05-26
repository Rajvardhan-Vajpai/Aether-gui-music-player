# Aether Player - GUI & Feature Improvements Summary

Welcome to the **Aether Player (Pixel Dreamscape Edition)**. The application has been redesigned from a basic utility into an immersive, premium, and interactive retro-pixel music experience. All core functionalities are preserved, but the interface, aesthetics, and user controls have been dramatically modernized.

---

## 🎨 Visual & Design Enhancements

### 1. Color Palette: Space Dreamscape Aesthetic
The color system has been updated from standard high-contrast greens to a cohesive, comforting dark mode theme:
*   **Primary Background**: Deep space dark (`#0A0E27`) for extreme visual comfort and low eye strain.
*   **Secondary Panels**: Muted indigo/slate (`#1A1F3A`) to define control zones.
*   **Primary Accent**: Warm pink/magenta (`#FF6B9D`) for core action controls.
*   **Secondary Accent**: Electric cyan (`#00D9FF`) for active statuses, borders, and scene highlights.
*   **Tertiary Accent**: Warm amber/yellow (`#FFD93D`) for volume markers and warm highlights.
*   **Typography & Text**: Soft white (`#E8E8FF`) for readability, and muted purple (`#A0A0C0`) for background details.
*   **Borders**: Subtle dark violet (`#2D2F4F`) to establish depth.

### 2. Retro-Pixel Typography & Geometric Controls
*   **Monospace Font**: The typography uses `Courier New` (falling back to the default monospace if needed) to achieve a digital clock and authentic retro feel.
*   **Square Corners**: Removed modern rounded corners in favor of a crisp pixel design (buttons use a tight border radius of `4px` or `2px`).
*   **Micro-Borders**: Semi-transparent border outlines on all buttons and panels enhance readability against dark backdrops.

### 3. Layered Transparent Glassmorphism
*   Controls use transparent alpha-blended glass surfaces (`C["glass"]` and `C["glass_dark"]`) to allow the underlying animated scene backgrounds and particle fields to bleed through.

---

## ✨ Immersive Animations & Graphic Effects

### 1. Multi-Scene Environment Engine
*   **Pre-configured Pixel Scenes**: Support for 8 default pixel dreamscapes (Galaxy Night, Dark Fantasy, Cherry Blossom, Lotus Pond, Water Lilies, Koi Garden, Night Drive, Starry Night).
*   **Automatic Image Discovery**: The player scans its local directory for any files matching `scene_*.jpg/png/webp` or several online search names and automatically loads them into the rotation.
*   **Dynamic Cross-Fade Transitions**: When switching scenes, the old background gently fades out while the new scene fades in using an interpolated alpha overlay (`trans_t` timeline) to avoid jarring screen jumps.

### 2. Real-Time Scene-Aware Particle System
Spawns **70 active particles** that behave differently depending on the active visual scene:
*   `star` (Galaxy, Starry Night): Winking, twinkling stars that drift upward and change size/transparency.
*   `petal` (Cherry Blossom, Pond, Lilies): Rotating, falling pink/green blossom petals drifting diagonally.
*   `ember` (Dark Fantasy): Glowing orange/red fire embers floating upward.
*   `dust` (Night Drive): Soft, slow-moving ambient dust particles floating in space.

### 3. Active Audio Waveform Visualizer
*   Features a **24-channel audio waveform spectrum** that pulses dynamically above the controls.
*   The spectrum uses linear interpolation (LERP) to animate heights when music is playing, falling back to a gentle resting idle state when paused or stopped.

### 4. Breathing/Pulsing Micro-Animations
*   **Cover Art Pulse**: The cover art frame expands slightly when playing and shrinks when paused/stopped.
*   **Glow Animation**: The song title and the Play/Pause button dynamically pulse their glow intensity using a sine-wave function (`math.sin(self.breath_t)`) to make the interface feel alive.
*   **Vignette Overlay**: A layered dark vignette frames the window border to draw focus to the center playhead.

---

## 🛠️ Upgraded Control & Navigation Features

### 1. Slide-Out Scene Selection Panel
*   Clicking the small `⊞` icon in the top-right corner slides open a modern, glassmorphic panel containing all detected backgrounds.
*   Supports keyboard shortcut `TAB` to quickly rotate through scenes.

### 2. Native In-App Search Overlay
*   Replaced blocking, OS-native Tkinter dialogs with a beautiful, custom-styled dark glass in-app modal.
*   Includes a blinking input cursor, real-time download status indicator, and a results list showing the top 5 YouTube results.
*   Runs YouTube searches asynchronously via Python threads, ensuring the player never freezes while fetching or downloading files.
*   Supports navigation using the Up/Down arrow keys (or `W`/`S`), Enter to select, and mouse clicks.

### 3. Playback Loop Selector
*   Includes a dedicated Loop mode control supporting multiple settings:
    *   `∞` (Infinite loop)
    *   `×1` (Single play)
    *   `×3` / `×5` / `×10` (Specified repeat counts with a live counter overlay: `loop 1/3`).

### 4. Smooth Click & Drag Seekers
*   The track progress slider and volume slider support interactive clicking and smooth mouse dragging, adjusting the music seek-time and mixer volume instantly.

---

## 💻 Window & Execution Setup
*   **Compact Mode**: Runs in a fixed windowed frame of `520x760` (providing a snug, console-like widget appearance).
*   **App Title**: Set to `"Aether Player  ✦  Pixel Dreamscape"` to match the fantasy theme.
*   **Audio frequency**: Pre-configured to `44100Hz` for high-quality audio output.
