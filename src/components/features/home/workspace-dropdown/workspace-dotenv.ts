export interface WorkspaceEnvVar {
  key: string;
  value: string;
}

const ENV_KEY_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

export function isValidEnvVarKey(key: string): boolean {
  return ENV_KEY_PATTERN.test(key.trim());
}

export function parseDotenv(raw: string): WorkspaceEnvVar[] {
  const vars: WorkspaceEnvVar[] = [];
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const separator = trimmed.indexOf("=");
    if (separator < 1) continue;
    const key = trimmed.slice(0, separator).trim();
    let value = trimmed.slice(separator + 1);
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (!isValidEnvVarKey(key)) continue;
    vars.push({ key, value });
  }
  return vars;
}

export function serializeDotenv(vars: WorkspaceEnvVar[]): string {
  const lines = vars
    .map((entry) => ({ key: entry.key.trim(), value: entry.value }))
    .filter((entry) => isValidEnvVarKey(entry.key))
    .map((entry) => {
      const needsQuotes = /[\s#"']/.test(entry.value);
      const value = needsQuotes
        ? `"${entry.value.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`
        : entry.value;
      return `${entry.key}=${value}`;
    });
  return lines.length === 0 ? "" : `${lines.join("\n")}\n`;
}
