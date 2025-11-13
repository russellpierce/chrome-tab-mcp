// Get the current tab and display its title
chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
  const currentTab = tabs[0];
  const tabTitle = currentTab.title;

  // Display the title in the popup
  document.getElementById('tabTitle').textContent = tabTitle;
});
