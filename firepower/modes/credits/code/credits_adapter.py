"""Native credit ledger without changing Firepower's existing start policy.

Pricing, awards, audits, strings and free-play use native Credits. Optional
unrestricted starts preserve the cabinet policy; HSTD alone uses L-6's
one-check award cap while Match and ordinary purchases retain the configured cap.
"""
from mpf.modes.credits.code.credits import Credits


class CreditsAdapter(Credits):
    _rom_hstd_batch = False

    @staticmethod
    def get_config_spec():
        return {'unrestricted_starts': 'single|bool|true'}

    def enable_credit_play(self, post_event=True, **kwargs):
        super().enable_credit_play(post_event=post_event, **kwargs)
        if self.config['mode_settings']['unrestricted_starts']:
            self._remove_event_handlers()

    def _add_credit_units(self, credit_units, price_tiering=True):
        if self._rom_hstd_batch:
            # L-6 checks its cap once before the HSTD batch, then increments
            # every 16 ticks even across the cap. Use native awards/audits;
            # scope the native API's per-increment cap exemption to this call.
            original = self.credits_config['max_credits']
            self.credits_config['max_credits'] = self.machine.placeholder_manager.build_int_template(0)
            try:
                super()._add_credit_units(credit_units, price_tiering=False)
            finally:
                self.credits_config['max_credits'] = original
                self._control_coin_inhibit()
            return
        maximum = self.credits_config['max_credits'].evaluate([]) * self.credit_units_per_game
        if maximum and self._get_credit_units() >= maximum:
            # Native dev4 would reduce an already overshot ROM batch to its
            # cap on the next rejected award/coin. Reject without erasing it.
            self.machine.events.post('max_credits_reached')
            self._control_coin_inhibit()
            return
        # Installed MPF may overwrite its cap after a fractional non-purchase
        # award. Bound the native API input; never write credit variables here.
        if not price_tiering:
            maximum = self.credits_config['max_credits'].evaluate([]) * self.credit_units_per_game
            if maximum:
                credit_units = min(credit_units, max(0, maximum - self._get_credit_units()))
        super()._add_credit_units(credit_units, price_tiering=price_tiering)

    def _credit_event_callback(self, credits_value, audit_class, rom_hstd_batch=False, **kwargs):
        self._rom_hstd_batch = bool(rom_hstd_batch and audit_class == 'high_score_to_date')
        try:
            super()._credit_event_callback(credits_value, audit_class, **kwargs)
        finally:
            self._rom_hstd_batch = False
