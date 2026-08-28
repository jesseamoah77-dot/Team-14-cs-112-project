// Client-side validation for instant feedback. Everything here is convenience -
// the server re-validates all of it, so disabling JavaScript changes nothing about
// what the system accepts.

document.addEventListener("DOMContentLoaded", function () {
  // Registration: swap the clinic picker / clinic-name field with the role,
  // and adjust the ID hint to the selected role's rule.
  var form = document.getElementById("register-form");
  if (form) {
    var hint = document.getElementById("id-hint");
    var clinicPick = document.getElementById("clinic-pick");
    var clinicName = document.getElementById("clinic-name");
    function applyRole() {
      var clinician = document.getElementById("role-clinician").checked;
      clinicPick.classList.toggle("d-none", clinician);
      clinicName.classList.toggle("d-none", !clinician);
      hint.textContent = clinician
        ? "Clinician IDs end in 0000, e.g. 12350000."
        : "Patient IDs end in your registration year (2022–2028), e.g. 12342024.";
    }
    form.querySelectorAll("input[name=role]").forEach(function (radio) {
      radio.addEventListener("change", applyRole);
    });
    applyRole();

    // Live password feedback listing what's still missing.
    var password = document.getElementById("password");
    var feedback = document.getElementById("password-feedback");
    password.addEventListener("input", function () {
      var v = password.value;
      var missing = [];
      if (v.length < 8) missing.push("8+ characters");
      if (!/[A-Z]/.test(v)) missing.push("uppercase");
      if (!/[a-z]/.test(v)) missing.push("lowercase");
      if (!/\d/.test(v)) missing.push("digit");
      if (!/[!@#$%^&*]/.test(v)) missing.push("special (!@#$%^&*)");
      feedback.textContent = missing.length ? "Still needs: " + missing.join(", ") : "";
      feedback.className = missing.length ? "small text-danger" : "small text-success";
      if (!missing.length) feedback.textContent = "Password meets the requirements.";
    });
  }

  // Upload form: reject wrong extensions before the round-trip.
  var fileInput = document.getElementById("file");
  if (fileInput) {
    var fileFeedback = document.getElementById("file-feedback");
    fileInput.addEventListener("change", function () {
      var name = (fileInput.files[0] || {}).name || "";
      var ok = /\.(txt|csv|pdf)$/i.test(name);
      fileFeedback.textContent = ok || !name
        ? "" : "Only .txt, .csv and .pdf files are accepted.";
    });
  }
});
