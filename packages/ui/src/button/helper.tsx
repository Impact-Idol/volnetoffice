export type TButtonVariant =
  | "primary"
  | "accent-primary"
  | "outline-primary"
  | "neutral-primary"
  | "link-primary"
  | "danger"
  | "accent-danger"
  | "outline-danger"
  | "link-danger"
  | "tertiary-danger"
  | "link-neutral"
  // Impact Idol Design System Variants
  | "ii-primary"
  | "ii-secondary"
  | "ii-destructive"
  | "ii-ghost"
  | "ii-outline"
  | "ii-link";

export type TButtonSizes = "sm" | "md" | "lg" | "xl";

export interface IButtonStyling {
  [key: string]: {
    default: string;
    hover: string;
    pressed: string;
    disabled: string;
  };
}

enum buttonSizeStyling {
  sm = `px-3 py-1.5 font-medium text-11 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
  md = `px-4 py-1.5 font-medium text-13 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
  lg = `px-5 py-2 font-medium text-13 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
  xl = `px-5 py-3.5 font-medium text-13 rounded-sm flex items-center gap-1.5 whitespace-nowrap transition-all justify-center`,
}

// Impact Idol button sizes with 44px minimum touch targets (WCAG 2.5.5)
enum iiButtonSizeStyling {
  sm = `px-3 py-2 font-medium text-sm rounded-[0.5rem] flex items-center gap-2 whitespace-nowrap transition-all justify-center min-h-[36px]`,
  md = `px-4 py-2.5 font-medium text-sm rounded-[0.5rem] flex items-center gap-2 whitespace-nowrap transition-all justify-center min-h-[44px] min-w-[44px]`,
  lg = `px-5 py-3 font-medium text-base rounded-[0.5rem] flex items-center gap-2 whitespace-nowrap transition-all justify-center min-h-[48px] min-w-[48px]`,
  xl = `px-6 py-4 font-medium text-base rounded-[0.5rem] flex items-center gap-2 whitespace-nowrap transition-all justify-center min-h-[56px] min-w-[56px]`,
}

enum buttonIconStyling {
  sm = "h-3 w-3 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0",
  md = "h-3.5 w-3.5 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0",
  lg = "h-4 w-4 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0",
  xl = "h-4 w-4 flex justify-center items-center overflow-hidden my-0.5 flex-shrink-0 ",
}

export const buttonStyling: IButtonStyling = {
  primary: {
    default: `text-on-color bg-accent-primary`,
    hover: `hover:bg-accent-primary/80`,
    pressed: `focus:text-custom-brand-40 focus:bg-accent-primary/80`,
    disabled: `cursor-not-allowed !bg-layer-1 !text-on-color-disabled`,
  },
  "accent-primary": {
    default: `bg-accent-primary/20 text-accent-primary`,
    hover: `hover:bg-accent-primary/10 hover:text-accent-secondary`,
    pressed: `focus:bg-accent-primary/10`,
    disabled: `cursor-not-allowed !text-accent-primary/60`,
  },
  "outline-primary": {
    default: `text-accent-primary bg-transparent border border-accent-strong`,
    hover: `hover:bg-accent-primary/20`,
    pressed: `focus:text-accent-primary focus:bg-accent-primary/30`,
    disabled: `cursor-not-allowed !text-accent-primary/60 !border-accent-strong-60 `,
  },
  "neutral-primary": {
    default: `text-secondary bg-surface-1 border border-subtle`,
    hover: `hover:bg-surface-2`,
    pressed: `focus:text-tertiary focus:bg-surface-2`,
    disabled: `cursor-not-allowed !bg-layer-1 !text-placeholder`,
  },
  "link-primary": {
    default: `text-accent-primary bg-surface-1`,
    hover: `hover:text-accent-secondary`,
    pressed: `focus:text-accent-primary/80 `,
    disabled: `cursor-not-allowed !text-accent-primary/60`,
  },
  danger: {
    default: `bg-danger-primary text-on-color`,
    hover: ` hover:bg-danger-primary-hover`,
    pressed: `focus:bg-danger-primary-active`,
    disabled: `cursor-not-allowed bg-layer-disabled! text-disabled!`,
  },
  "accent-danger": {
    default: `text-danger-primary bg-red-50`,
    hover: `hover:text-danger-primary hover:bg-red-100`,
    pressed: `focus:text-danger-primary focus:bg-red-100`,
    disabled: `cursor-not-allowed !bg-layer-1 !text-placeholder`,
  },
  "outline-danger": {
    default: `bg-layer-2 text-danger-primary border border-danger-strong`,
    hover: `hover:bg-danger-subtle`,
    pressed: `focus:bg-danger-subtle-hover`,
    disabled: `cursor-not-allowed text-disabled! border-subtle-1!`,
  },
  "link-danger": {
    default: `text-danger-primary bg-surface-1`,
    hover: `hover:text-danger-primary`,
    pressed: `focus:text-danger-primary`,
    disabled: `cursor-not-allowed !bg-layer-1 !text-placeholder`,
  },
  "tertiary-danger": {
    default: `text-danger-primary bg-surface-1 border border-danger-subtle`,
    hover: `hover:bg-red-50 hover:border-danger-subtle`,
    pressed: `focus:text-danger-primary`,
    disabled: `cursor-not-allowed !bg-layer-1 !text-placeholder`,
  },
  "link-neutral": {
    default: `text-tertiary`,
    hover: `hover:text-secondary`,
    pressed: `focus:text-primary`,
    disabled: `cursor-not-allowed !bg-layer-1 !text-placeholder`,
  },
  // Impact Idol Design System Button Variants
  "ii-primary": {
    default: `bg-[hsl(210_100%_50%)] text-white`,
    hover: `hover:bg-[hsl(210_100%_45%)]`,
    pressed: `focus:bg-[hsl(210_100%_40%)] focus:ring-2 focus:ring-[hsl(210_100%_70%)] focus:ring-offset-2`,
    disabled: `cursor-not-allowed !bg-[hsl(210_20%_80%)] !text-[hsl(210_10%_60%)]`,
  },
  "ii-secondary": {
    default: `bg-transparent text-[hsl(217.2_32.6%_17.5%)] border border-[hsl(214.3_31.8%_91.4%)]`,
    hover: `hover:bg-[hsl(210_40%_98%)] hover:border-[hsl(214.3_31.8%_85%)]`,
    pressed: `focus:bg-[hsl(210_40%_96%)] focus:ring-2 focus:ring-[hsl(210_100%_70%)] focus:ring-offset-2`,
    disabled: `cursor-not-allowed !bg-transparent !text-[hsl(215.4_20.2%_65.1%)] !border-[hsl(214.3_31.8%_91.4%)]`,
  },
  "ii-destructive": {
    default: `bg-[hsl(0_84.2%_60.2%)] text-white`,
    hover: `hover:bg-[hsl(0_84.2%_55%)]`,
    pressed: `focus:bg-[hsl(0_84.2%_50%)] focus:ring-2 focus:ring-[hsl(0_84.2%_80%)] focus:ring-offset-2`,
    disabled: `cursor-not-allowed !bg-[hsl(0_30%_80%)] !text-[hsl(0_10%_60%)]`,
  },
  "ii-ghost": {
    default: `bg-transparent text-[hsl(217.2_32.6%_17.5%)]`,
    hover: `hover:bg-[hsl(210_40%_96.1%)]`,
    pressed: `focus:bg-[hsl(210_40%_94%)] focus:ring-2 focus:ring-[hsl(210_100%_70%)] focus:ring-offset-2`,
    disabled: `cursor-not-allowed !text-[hsl(215.4_20.2%_65.1%)]`,
  },
  "ii-outline": {
    default: `bg-transparent text-[hsl(210_100%_50%)] border border-[hsl(210_100%_50%)]`,
    hover: `hover:bg-[hsl(210_100%_97%)]`,
    pressed: `focus:bg-[hsl(210_100%_95%)] focus:ring-2 focus:ring-[hsl(210_100%_70%)] focus:ring-offset-2`,
    disabled: `cursor-not-allowed !text-[hsl(210_50%_70%)] !border-[hsl(210_50%_70%)]`,
  },
  "ii-link": {
    default: `bg-transparent text-[hsl(210_100%_50%)] underline-offset-2`,
    hover: `hover:text-[hsl(210_100%_45%)] hover:underline`,
    pressed: `focus:text-[hsl(210_100%_40%)]`,
    disabled: `cursor-not-allowed !text-[hsl(210_50%_70%)]`,
  },
};

export const getButtonStyling = (variant: TButtonVariant, size: TButtonSizes, disabled: boolean = false): string => {
  let tempVariant: string = ``;
  const currentVariant = buttonStyling[variant];

  tempVariant = `${currentVariant.default} ${disabled ? currentVariant.disabled : currentVariant.hover} ${
    currentVariant.pressed
  }`;

  // Use Impact Idol sizing (with 44px touch targets) for ii-* variants
  let tempSize: string = ``;
  if (size) {
    const isImpactIdolVariant = variant.startsWith("ii-");
    tempSize = isImpactIdolVariant ? iiButtonSizeStyling[size] : buttonSizeStyling[size];
  }
  return `${tempVariant} ${tempSize}`;
};

export const getIconStyling = (size: TButtonSizes): string => {
  let icon: string = ``;
  if (size) icon = buttonIconStyling[size];
  return icon;
};
