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
      // A plain label, not a toolbarbutton: toolbar buttons can hide their text in icon mode
      const clock = aDocument.createXULElement("label");
      clock.id = WIDGET_ID;
      clock.setAttribute("value", formatter.format(new Date()));
      clock.style.padding = "0 10px";
      clock.style.alignSelf = "center";
      return clock;
    },
  });

  // One timer updates the clock in every open browser window
  setInterval(() => {
    const text = formatter.format(new Date());
    for (const win of Services.wm.getEnumerator("navigator:browser")) {
      win.document.getElementById(WIDGET_ID)?.setAttribute("value", text);
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
      });
    }
  }, 5000);
})();
