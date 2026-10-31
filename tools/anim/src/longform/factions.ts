// Crowd factions for the code-drawn stick soldiers. Placeholder colours; Plan 5 fixes them from sources.
export type Faction = 'daiviet' | 'nguyen';
export type FactionLook = {skin: string; tunic: string; helmet: 'round' | 'cone'; weapon: 'spear' | 'sword'; shield: boolean};

export const FACTIONS: Record<Faction, FactionLook> = {
  daiviet: {skin: '#b9773f', tunic: '#7a4e2d', helmet: 'round', weapon: 'spear', shield: true},
  nguyen: {skin: '#c58a52', tunic: '#3f6b73', helmet: 'cone', weapon: 'sword', shield: true},
};

export const INK = '#2b2118';
