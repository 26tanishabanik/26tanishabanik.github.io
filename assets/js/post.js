(function () {
  var body = document.querySelector(".post-body");
  if (!body) return;

  // Images on their own line become figures, captioned with their alt text.
  body.querySelectorAll("p > img:only-child").forEach(function (img) {
    var p = img.parentNode;
    if (p.textContent.trim() !== "") return;
    var fig = document.createElement("figure");
    fig.appendChild(img);
    if (img.alt) {
      var cap = document.createElement("figcaption");
      cap.textContent = img.alt;
      fig.appendChild(cap);
    }
    p.replaceWith(fig);
  });

  var toc = document.getElementById("markdown-toc");
  if (!toc) return;
  toc.removeAttribute("id");
  toc.className = "toc-list";

  // Narrow screens: a collapsed contents block where the list was.
  var inline = document.createElement("details");
  inline.className = "toc-inline";
  var summary = document.createElement("summary");
  summary.textContent = "Contents";
  inline.appendChild(summary);
  toc.parentNode.insertBefore(inline, toc);
  inline.appendChild(toc);

  // Wide screens: a sticky rail that follows the reader.
  var rail = document.querySelector(".toc-rail");
  if (!rail) return;
  var label = document.createElement("p");
  label.className = "toc-label";
  label.textContent = "Contents";
  rail.appendChild(label);
  var list = toc.cloneNode(true);
  rail.appendChild(list);

  var links = Array.prototype.slice.call(list.querySelectorAll("a"));
  var heads = links
    .map(function (a) { return document.getElementById(decodeURIComponent(a.hash.slice(1))); })
    .filter(Boolean);

  var ticking = false;
  function update() {
    ticking = false;
    var current = -1;
    for (var i = 0; i < heads.length; i++) {
      if (heads[i].getBoundingClientRect().top < 140) current = i;
    }
    links.forEach(function (a, i) { a.classList.toggle("active", i === current); });
  }
  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  }, { passive: true });
  update();
})();
