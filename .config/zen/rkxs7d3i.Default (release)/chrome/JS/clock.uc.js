// ==UserScript==
// @name           Nav bar clock
// @description    Shows the current time in the nav bar, after the extensions button
// ==/UserScript==

(() => {
  // Every browser window runs this script, but the widget only needs registering once
  if (Services.clockInstalled) return;
  Services.clockInstalled = true;

  const { CustomizableUI } = ChromeUtils.importESModule(
    "resource:///modules/CustomizableUI.sys.mjs"
  );

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
      const button = aDocument.createXULElement("toolbarbutton");
      button.id = WIDGET_ID;
      button.className = "toolbarbutton-1 chromeclass-toolbar-additional";
      button.setAttribute("label", formatter.format(new Date()));
      button.setAttribute("tooltiptext", "Current time");
      return button;
    },
  });

  // One timer updates the clock in every open browser window
  setInterval(() => {
    const text = formatter.format(new Date());
    for (const win of Services.wm.getEnumerator("navigator:browser")) {
      win.document.getElementById(WIDGET_ID)?.setAttribute("label", text);
    }
  }, 1000);
})();
