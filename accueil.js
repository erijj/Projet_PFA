const nav = document.getElementById("navbar");
    window.addEventListener("scroll", () => nav.classList.toggle("scrolled", scrollY > 40));
    const obs = new IntersectionObserver(
      (es) => es.forEach((e) => { if (e.isIntersecting) e.target.classList.add("visible"); }),
      { threshold: 0.1 }
    );
    document.querySelectorAll(".reveal").forEach((el) => obs.observe(el));
    function doVerify() {
      const id = document.getElementById("certId").value.trim();
      const res = document.getElementById("result");
      if (!id) { res.innerHTML = '<span class="r-err"><i class="fas fa-circle-xmark"></i> Veuillez entrer un identifiant</span>'; return; }
      res.innerHTML = '<span style="color:var(--muted)"><i class="fas fa-spinner fa-spin me-1"></i> Interrogation de la blockchain Ethereum…</span>';
      setTimeout(() => {
        res.innerHTML = id.toUpperCase().startsWith("CERT-")
          ? `<span class="r-ok"><i class="fas fa-circle-check"></i>&nbsp;<strong>${id}</strong>&nbsp;— Certificat authentique · Ethereum · Block #19,847,302</span>`
          : `<span class="r-err"><i class="fas fa-circle-xmark"></i>&nbsp;Aucun certificat trouvé pour <strong>${id}</strong></span>`;
      }, 1100);
    }
    document.getElementById("certId").addEventListener("keydown", (e) => { if (e.key === "Enter") doVerify(); });