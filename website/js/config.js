export const REPO = "cfopuser/app-store";
export const RELEASES_API = `https://api.github.com/repos/${REPO}/releases`;
export const APPS_DIR = "apps";
export let REGISTERED_APPS = [];

export function setRegisteredApps(apps) {
    REGISTERED_APPS = apps;
}
