// Channel palette and font (same values as tools/kit/build_visuals.py).
import fontUrl from './fonts/PatrickHand-Regular.ttf'; // SIL OFL 1.1, see fonts/LICENSE_PatrickHand.txt

export const INK = '#1b1b1b';
export const PAPER = '#FAF7F0';
export const ACC = '#D9480F';
export const ACC_L = '#FBD9C6';
export const GREY = '#8a8a85';
export const GREEN = '#e9f2df';
export const GOLD = '#f6d77a';
export const SKY = '#9fb3c4';
export const WHITE = '#fff';

export const FONT = "'PatrickHand', cursive";
export const FONT_URL: string = fontUrl;

// Drawings use a 1920x1080 space; the composition scales it to the output size (2560x1440).
export const DW = 1920;
export const DH = 1080;
export const FPS = 30;
