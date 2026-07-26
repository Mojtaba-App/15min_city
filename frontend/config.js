/* Local dashboard config — change API_ORIGIN if the backend host/port differs. */
window.APP_CONFIG = {
  API_ORIGIN: "http://127.0.0.1:8001",
  get API_BASE() {
    return `${this.API_ORIGIN}/accessibility`;
  },
};
