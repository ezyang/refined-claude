// Popup script for managing extension settings

document.addEventListener('DOMContentLoaded', async () => {
  const autoContinueToggle = document.getElementById('autoContinueToggle');

  // Load the current setting from storage
  try {
    // Get the current settings from chrome.storage.sync
    const result = await chrome.storage.sync.get({ autoContinueEnabled: true });

    // Update the checkbox to reflect the current setting
    autoContinueToggle.checked = result.autoContinueEnabled;

    console.log('Loaded setting:', result.autoContinueEnabled);
  } catch (error) {
    console.error('Error loading settings:', error);
  }

  // Add event listener for the toggle
  autoContinueToggle.addEventListener('change', async () => {
    try {
      // Save the new setting to chrome.storage.sync
      await chrome.storage.sync.set({ autoContinueEnabled: autoContinueToggle.checked });

      console.log('Saved setting:', autoContinueToggle.checked);

      // Send a message to any active tabs to update their behavior immediately
      const tabs = await chrome.tabs.query({ url: ['*://*.claude.ai/*', '*://localhost/*'] });

      for (const tab of tabs) {
        try {
          await chrome.tabs.sendMessage(tab.id, {
            action: 'updateSettings',
            settings: { autoContinueEnabled: autoContinueToggle.checked },
          });
          console.log('Sent settings update to tab:', tab.id);
        } catch (err) {
          // It's normal for this to fail if the content script isn't running on the tab
          console.log('Could not update tab:', tab.id, err);
        }
      }
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  });
});
