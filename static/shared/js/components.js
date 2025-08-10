// Alpine.js reusable components
function timezoneDropdown({ inputId, initial }) {
  return {
    open: false,
    query: '',
    zones: [],
    selected: initial || '',
    init() {
      // Populate full IANA list if supported
      if (typeof Intl !== 'undefined' && typeof Intl.supportedValuesOf === 'function') {
        try { this.zones = Intl.supportedValuesOf('timeZone') || []; } catch (e) {}
      }
      if (!this.zones.length) {
        this.zones = [
          'UTC','Europe/London','Europe/Berlin','America/New_York','America/Chicago','America/Denver','America/Los_Angeles','Asia/Tokyo'
        ];
      }
      // Default selection
      if (!this.selected) {
        const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        this.selected = (browserTz && this.zones.includes(browserTz)) ? browserTz : 'UTC';
      }
      const input = document.getElementById(inputId);
      if (input) input.value = this.selected;
    },
    filtered() {
      const q = this.query.trim().toLowerCase();
      if (!q) return this.zones;
      return this.zones.filter(z => z.toLowerCase().includes(q));
    },
    choose(tz) {
      this.selected = tz;
      const input = document.getElementById(inputId);
      if (input) input.value = tz;
      this.open = false;
      // Focus back to button for accessibility
      this.$nextTick(() => {
        try { this.$el.querySelector('button[type="button"]').focus(); } catch(e) {}
      });
    }
  };
}

