$(document).ready(function () {
  $("#sidebar-toggler").on("click", function () {
    $("#sidebar-upper").toggleClass("toggled");
    $("#sidebar-lower").toggleClass("toggled");
  });
});

// http://jsfiddle.net/bknE4/81/
function addParam(url, param, value) {
  var a = document.createElement("a"),
    regex = /(?:\?|&amp;|&)+([^=]+)(?:=([^&]*))*/g;
  var match,
    str = [];
  a.href = url;
  param = encodeURIComponent(param);
  var exists = false;
  var existsText = "";

  while ((match = regex.exec(a.search))) {
    if (param != match[1]) {
      str.push(match[1] + (match[2] ? "=" + match[2] : ""));
    }
    if (param == match[1]) {
      exists = true;
      existsText = match[2];
    }
  }

  if (!exists || (exists && existsText != encodeURIComponent(value)))
    str.push(param + (value ? "=" + encodeURIComponent(value) : ""));
  a.search = str.join("&");

  document.location.href = a.href;
}
