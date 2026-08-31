import { none } from "eve/channels/auth";
import { eveChannel } from "eve/channels/eve";

/** Harbor / gold-lab fixture: admit the browser without Vercel OIDC. */
export default eveChannel({
  auth: [none()],
});
