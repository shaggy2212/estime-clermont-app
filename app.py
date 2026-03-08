<iframe 
  id="icostim-frame"
  src="https://estime-clermont-app-jq8fmfdn95ggqtukbncztr.streamlit.app/?embed=true"
  style="width:100%; height:2000px; border:0; display:block; overflow:hidden;"
  scrolling="no"
  allow="geolocation"
></iframe>

<script>
(function () {
  var iframe = document.getElementById("icostim-frame");
  if (!iframe) return;

  function isMobile() {
    return window.matchMedia("(max-width: 768px)").matches;
  }

  function heightForm()    { return isMobile() ? 3400 : 2000; }
  function heightResults() { return isMobile() ? 6200 : 4400; }

  function setHeight(h) {
    iframe.style.height    = h + "px";
    iframe.style.minHeight = h + "px";
  }

  // Init
  setHeight(heightForm());

  // Écoute les messages depuis Streamlit
  window.addEventListener("message", function (e) {
    if (!e.data || typeof e.data !== "object") return;
    console.log("[ICOstim embed] message reçu:", JSON.stringify(e.data).substring(0, 200));

    if (e.data.type === "icostim:resultsReady") {
      setHeight(heightResults());
    }
    if (e.data.type === "streamlit:setFrameHeight") {
      var h = Math.ceil(e.data.height) + 120;
      if (h > heightForm()) setHeight(h);
    }
  });

  window.addEventListener("resize", function() { setHeight(heightForm()); });
})();
</script>
