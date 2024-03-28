function show() {
    var x = document.getElementById("password_profile");
    if (x.type === "password") {
      x.type = "text";
    } else {
      x.type = "password";
    }
  }