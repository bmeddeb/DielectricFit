/**
 * Alpine.js reusable components
 *
 * Generic select-style dropdown you can reuse across the app.
 *
 * Usage (HTML):
 *   <div x-data="selectDropdown({
 *          inputId: 'my-input',               // required: id of hidden input to write value
 *          items: myItemsArrayOrNull,         // optional: array of strings or objects
 *          valueKey: 'id',                    // for object items, which key is the value
 *          labelKey: 'label',                 // for object items, which key is the label
 *          initial: 'defaultValue',           // optional initial value
 *          placeholder: 'Select an option',   // optional placeholder label
 *          loader: () => Promise.resolve([]), // optional async loader returning items
 *          onChange: (val) => {}              // optional callback on selection change
 *        })">
 *     ... replicate markup similar to timezoneDropdown or compose your own ...
 *   </div>
 */
function selectDropdown(cfg = {}) {
  const valueKey = cfg.valueKey || 'value';
  const labelKey = cfg.labelKey || 'label';
  return {
    open: false,
    query: '',
    items: Array.isArray(cfg.items) ? cfg.items : [],
    selected: cfg.initial || '',
    placeholder: cfg.placeholder || 'Select an option',
    init() {
      const maybeLoad = typeof cfg.loader === 'function'
        ? Promise.resolve(cfg.loader())
        : Promise.resolve(null);
      maybeLoad.then(loaded => {
        if (Array.isArray(loaded)) this.items = loaded;
      }).finally(() => {
        if (!this.selected && this.items.length) {
          const first = this.items[0];
          this.selected = typeof first === 'object' ? first[valueKey] : first;
        }
        const input = document.getElementById(cfg.inputId);
        if (input) input.value = this.selected;
      });
    },
    toLabel(item) {
      return typeof item === 'object' ? (item[labelKey] ?? item[valueKey]) : item;
    },
    toValue(item) {
      return typeof item === 'object' ? item[valueKey] : item;
    },
    filtered() {
      const q = this.query.trim().toLowerCase();
      const arr = this.items || [];
      if (!q) return arr;
      return arr.filter(item => this.toLabel(item).toLowerCase().includes(q));
    },
    choose(item) {
      const val = this.toValue(item);
      this.selected = val;
      const input = document.getElementById(cfg.inputId);
      if (input) input.value = val;
      if (typeof cfg.onChange === 'function') cfg.onChange(val);
      this.open = false;
      this.$nextTick(() => {
        try { this.$el.querySelector('button[type="button"]').focus(); } catch(e) {}
      });
    }
  };
}

/**
 * Specialization: timezone dropdown built atop selectDropdown.
 * Provides full IANA list (via Intl.supportedValuesOf fallback) and sensible defaults.
 */
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
// Export to window (optional; Alpine will still see functions in global scope)
window.selectDropdown = window.selectDropdown || selectDropdown;
window.timezoneDropdown = window.timezoneDropdown || timezoneDropdown;
