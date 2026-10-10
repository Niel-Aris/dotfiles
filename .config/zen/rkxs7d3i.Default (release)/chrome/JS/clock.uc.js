// ==UserScript==
// @name           Nav bar clock
// @description    Shows the current time in the nav bar, after the extensions button
// ==/UserScript==

(() => {
  // Every browser window runs this script, but the widget only needs registering once
  if (Services.clockInstalled) return;
  Services.clockInstalled = true;

  // CustomizableUI is already a global in browser windows; its resource:///modules path doesn't load in Zen
  const WIDGET_ID = "custom-clock";
  const formatter = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  CustomizableUI.createWidget({
    id: WIDGET_ID,
    defaultArea: CustomizableUI.AREA_NAVBAR,
    removable: true,
    onBuild(aDocument) {
      // An HTML span sizes itself to its text; the XUL label stayed at 30px inside the nav bar
      const clock = aDocument.createElementNS("http://www.w3.org/1999/xhtml", "span");
      clock.id = WIDGET_ID;
      clock.textContent = formatter.format(new Date());
      const style = (prop, value) => clock.style.setProperty(prop, value, "important");
      style("padding", "0 10px");
      style("align-self", "center");
      style("white-space", "nowrap");
      style("color", "var(--toolbar-color)");
      style("flex", "0 0 auto");
      style("width", "max-content");
      style("min-width", "max-content");
      return clock;
    },
  });

  // One timer updates the clock in every open browser window
  setInterval(() => {
    const text = formatter.format(new Date());
    for (const win of Services.wm.getEnumerator("navigator:browser")) {
      const node = win.document.getElementById(WIDGET_ID);
      if (node) node.textContent = text;
    }
  }, 1000);

  // Temporary diagnostics: log where the clock ended up in each window
  setTimeout(() => {
    for (const win of Services.wm.getEnumerator("navigator:browser")) {
      const node = win.document.getElementById(WIDGET_ID);
      const bar = win.document.getElementById("nav-bar");
      console.log("clock diagnostics", {
        found: !!node,
        parent: node?.parentNode?.id,
        width: node?.getBoundingClientRect().width,
        navBarWidth: bar?.getBoundingClientRect().width,
        navBarDisplay: bar && win.getComputedStyle(bar).display,
        value: node?.textContent,
        display: node && win.getComputedStyle(node).display,
        maxWidth: node && win.getComputedStyle(node).maxWidth,
        scrollWidth: node?.scrollWidth,
        color: node && win.getComputedStyle(node).color,
        fontSize: node && win.getComputedStyle(node).fontSize,
        height: node?.getBoundingClientRect().height,
      });
    }
  }, 5000);
})();
