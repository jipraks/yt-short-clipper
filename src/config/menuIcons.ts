import {
  Bell,
  BookOpen,
  CircleHelp,
  Coins,
  CreditCard,
  Download,
  ExternalLink,
  Gift,
  Globe,
  GraduationCap,
  Instagram,
  LifeBuoy,
  Link,
  Megaphone,
  MessageCircle,
  MessageSquareText,
  MessagesSquare,
  Newspaper,
  PlayCircle,
  Rocket,
  Send,
  ShoppingCart,
  Sparkles,
  Star,
  Users,
  Video,
  Wallet,
  Youtube,
  Zap,
  type LucideIcon,
} from "lucide-react";

/**
 * Icons the menu API is allowed to name, keyed by the kebab-case name it sends.
 *
 * Lucide icons are React components resolved at build time, so an API can only
 * ever send a string — this registry is the bridge. It is deliberately an
 * allowlist: only these icons end up in the bundle, and a compromised or
 * mistyped response can never pull in code, only miss a lookup.
 *
 * To offer the API a new icon, add it here and ship an app update. Everything
 * already listed can be switched from the server with no release.
 */
export const MENU_ICONS: Record<string, LucideIcon> = {
  bell: Bell,
  "book-open": BookOpen,
  coins: Coins,
  "credit-card": CreditCard,
  download: Download,
  "external-link": ExternalLink,
  gift: Gift,
  globe: Globe,
  "graduation-cap": GraduationCap,
  "help-circle": CircleHelp,
  instagram: Instagram,
  "life-buoy": LifeBuoy,
  link: Link,
  megaphone: Megaphone,
  "message-circle": MessageCircle,
  "message-square-text": MessageSquareText,
  "messages-square": MessagesSquare,
  newspaper: Newspaper,
  "play-circle": PlayCircle,
  rocket: Rocket,
  send: Send,
  "shopping-cart": ShoppingCart,
  sparkles: Sparkles,
  star: Star,
  users: Users,
  video: Video,
  wallet: Wallet,
  youtube: Youtube,
  zap: Zap,
};

/** Shown when the API names an icon this build does not know. */
export const FALLBACK_MENU_ICON: LucideIcon = ExternalLink;

export function menuIcon(name: string | undefined): LucideIcon {
  if (!name) return FALLBACK_MENU_ICON;
  return MENU_ICONS[name.trim().toLowerCase()] ?? FALLBACK_MENU_ICON;
}
