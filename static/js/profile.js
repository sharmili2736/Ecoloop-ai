/* =========================================================================
   profile.js — profile updates, password change and preferences.
   ========================================================================= */

(function () {
  "use strict";

  const Eco = window.Eco;

  document.addEventListener("DOMContentLoaded", function () {
    Eco.$$("[data-fill]").forEach((s) => Eco.setBar(s, s.getAttribute("data-fill")));
  });

  /* ------------------------------------------------------------ profile */
  Eco.$("#profileForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    Eco.$("#nameError").textContent = "";

    const name = Eco.$("#name").value.trim();
    if (name.length < 2) { Eco.$("#nameError").textContent = "Enter your full name."; return; }

    const btn = Eco.$("#saveProfile");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';

    const res = await Eco.api("/api/profile", {
      method: "PUT",
      body: {
        name: name,
        organization: Eco.$("#organization").value.trim(),
        user_type: Eco.$("#userType").value,
        theme: Eco.$("#themeSelect").value,
        notifications: Eco.$("#notifications").checked,
      },
    });

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save changes';

    if (!res.success) { Eco.toast(res.error, "error", "Could not save"); return; }
    Eco.toast(res.message, "success", "Profile updated");
    setTimeout(() => window.location.reload(), 800);
  });

  /* ----------------------------------------------------------- password */
  Eco.$("#passwordForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    Eco.$("#passwordError").textContent = "";

    const current = Eco.$("#currentPassword").value;
    const next = Eco.$("#newPassword").value;

    if (!current) { Eco.$("#passwordError").textContent = "Enter your current password."; return; }
    if (next.length < 6) { Eco.$("#passwordError").textContent = "Use at least 6 characters."; return; }

    const btn = Eco.$("#savePassword");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';

    const res = await Eco.api("/api/profile/password", {
      method: "PUT",
      body: { current_password: current, new_password: next },
    });

    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-key"></i> Change password';

    if (!res.success) {
      Eco.$("#passwordError").textContent = res.error;
      Eco.toast(res.error, "error", "Could not change password");
      return;
    }
    Eco.toast(res.message, "success", "Password changed");
    Eco.$("#passwordForm").reset();
  });

  /* -------------------------------------------------------- preferences */
  Eco.$("#themeSelect").addEventListener("change", function () {
    Eco.applyTheme(this.value);
  });

  Eco.$("#savePrefs").addEventListener("click", async function () {
    const res = await Eco.api("/api/profile", {
      method: "PUT",
      body: {
        name: Eco.$("#name").value.trim(),
        organization: Eco.$("#organization").value.trim(),
        user_type: Eco.$("#userType").value,
        theme: Eco.$("#themeSelect").value,
        notifications: Eco.$("#notifications").checked,
      },
    });
    if (!res.success) { Eco.toast(res.error, "error", "Could not save"); return; }
    Eco.toast("Preferences saved.", "success", "Updated");
  });

  /* --------------------------------------------------- secondary logout */
  const logout2 = Eco.$("#logoutBtn2");
  if (logout2) {
    logout2.addEventListener("click", async function (e) {
      e.preventDefault();
      const ok = await Eco.confirm({
        title: "Sign out?",
        message: "You will need to sign in again to reach your dashboard.",
        confirmText: "Sign out",
      });
      if (!ok) return;
      const res = await Eco.api("/api/logout", { method: "POST" });
      window.location.href = res.redirect || "/";
    });
  }
})();
