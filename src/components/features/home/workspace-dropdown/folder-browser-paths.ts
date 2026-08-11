const WINDOWS_RESERVED_NAME =
  /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i;

export function isWindowsDriveRoot(path: string): boolean {
  return /^[A-Za-z]:[\\/]?$/.test(path);
}

export function trimTrailingSeparators(path: string): string {
  const trimmed = path.replace(/[\\/]+$/, "");
  if (/^[A-Za-z]:$/.test(trimmed)) {
    const separator = path.includes("/") && !path.includes("\\") ? "/" : "\\";
    return `${trimmed}${separator}`;
  }
  return trimmed;
}

export function getParentPath(path: string): string | null {
  const trimmed = trimTrailingSeparators(path);
  if (!trimmed || trimmed === "/" || isWindowsDriveRoot(trimmed)) return null;

  const idx = Math.max(trimmed.lastIndexOf("/"), trimmed.lastIndexOf("\\"));
  if (idx < 0) return null;
  if (idx === 0) return "/";

  const parent = trimmed.slice(0, idx);
  if (/^[A-Za-z]:$/.test(parent)) {
    return `${parent}${trimmed[idx]}`;
  }

  return parent;
}

export function joinBrowsePath(parent: string, name: string): string {
  const trimmed = trimTrailingSeparators(parent);
  if (!trimmed || trimmed === "/") return `/${name}`;
  if (isWindowsDriveRoot(trimmed)) return `${trimmed}${name}`;
  const separator = parent.includes("\\") && !parent.includes("/") ? "\\" : "/";
  return `${trimmed}${separator}${name}`;
}

export function isValidWorkspaceFolderName(raw: string): boolean {
  const name = raw.trim();
  if (!name || name === "." || name === "..") return false;
  if (name.length > 255) return false;
  if (/[<>:"|?*\u0000-\u001f\\/]/.test(name)) return false;
  if (WINDOWS_RESERVED_NAME.test(name)) return false;
  return true;
}
