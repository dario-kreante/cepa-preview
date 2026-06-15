const REFRESH_KEY = "cepa_refresh";
let accessToken: string | null = null;

export const tokenStore = {
  getAccess: () => accessToken,
  setAccess: (t: string | null) => { accessToken = t; },
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  setRefresh: (t: string | null) => {
    if (t) localStorage.setItem(REFRESH_KEY, t);
    else localStorage.removeItem(REFRESH_KEY);
  },
  clear: () => { accessToken = null; localStorage.removeItem(REFRESH_KEY); },
};
