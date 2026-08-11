import {
  Bot,
  Crosshair,
  GitPullRequest,
  Package,
  Palette,
  PenLine,
  Plug,
  ShieldCheck,
  Workflow,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { SKILL_CATEGORY_IDS } from "@openhands/extensions/skills";
import { I18nKey } from "#/i18n/declaration";

export const INFORMATION_SECURITY_CATEGORY = "information-security" as const;

/** Bundled catalog categories plus Heimdall infosec skills. */
export const APP_SKILL_CATEGORY_IDS = [
  ...SKILL_CATEGORY_IDS,
  INFORMATION_SECURITY_CATEGORY,
] as const;

export type AppSkillCategoryId = (typeof APP_SKILL_CATEGORY_IDS)[number];

/** Display order in the facet rail. `other` last. */
export const SKILL_CATEGORY_ORDER: readonly AppSkillCategoryId[] = [
  "automations",
  INFORMATION_SECURITY_CATEGORY,
  "environment",
  "code-hosting",
  "agent-authoring",
  "code-quality",
  "integrations",
  "writing",
  "design",
  "other",
];

export const SKILL_CATEGORY_LABEL_KEYS: Record<AppSkillCategoryId, I18nKey> = {
  automations: I18nKey.SETTINGS$SKILLS_CATEGORY_AUTOMATIONS,
  [INFORMATION_SECURITY_CATEGORY]:
    I18nKey.SETTINGS$SKILLS_CATEGORY_INFORMATION_SECURITY,
  environment: I18nKey.SETTINGS$SKILLS_CATEGORY_ENVIRONMENT,
  "code-hosting": I18nKey.SETTINGS$SKILLS_CATEGORY_CODE_HOSTING,
  "agent-authoring": I18nKey.SETTINGS$SKILLS_CATEGORY_AGENT_AUTHORING,
  "code-quality": I18nKey.SETTINGS$SKILLS_CATEGORY_CODE_QUALITY,
  integrations: I18nKey.SETTINGS$SKILLS_CATEGORY_INTEGRATIONS,
  writing: I18nKey.SETTINGS$SKILLS_CATEGORY_WRITING,
  design: I18nKey.SETTINGS$SKILLS_CATEGORY_DESIGN,
  other: I18nKey.SETTINGS$SKILLS_CATEGORY_OTHER,
};

export const SKILL_CATEGORY_ICONS: Record<AppSkillCategoryId, LucideIcon> = {
  automations: Workflow,
  [INFORMATION_SECURITY_CATEGORY]: Crosshair,
  environment: Wrench,
  "code-hosting": GitPullRequest,
  "agent-authoring": Bot,
  "code-quality": ShieldCheck,
  integrations: Plug,
  writing: PenLine,
  design: Palette,
  other: Package,
};

/** The catalog uses `other` for a skill with no marketplace entry, so it means "uncategorized" there exactly as it does for a local skill. */
export const UNCATEGORIZED_SKILL_CATEGORY: AppSkillCategoryId = "other";

const KNOWN_CATEGORIES = new Set<string>(APP_SKILL_CATEGORY_IDS);

/** Local skills carry no category and a stale bundled catalog could carry one this build does not know; both degrade to `other` rather than an unrenderable facet value. */
export function getSkillCategory(skill: {
  category?: string | null;
}): AppSkillCategoryId {
  const raw = skill.category;
  if (raw && KNOWN_CATEGORIES.has(raw)) {
    return raw;
  }
  return UNCATEGORIZED_SKILL_CATEGORY;
}
