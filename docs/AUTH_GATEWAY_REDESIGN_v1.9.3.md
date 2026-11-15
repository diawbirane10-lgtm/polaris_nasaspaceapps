# POLARIS auth gateway — v1.9.3

The root route `/` and `/workspace` show only login or registration before authentication. No charts, atlas, engineering workflow overview, demo links or administrative navigation are rendered on the entry screen. `/demo` remains directly accessible by URL for the NASA judging link.

The existing sign-up, approval status, TOTP MFA, and private mission planning remain unchanged. Identity and authorization continue to be validated by backend APIs and Supabase RLS; hiding UI is not an authorization control. This change only adjusts the pre-auth presentation and has not activated any new privileged functionality.

Visual design follows the explicit Sport Programme design contract: white canvas, black text, #145dff blue labels, square panels, thin borders, low visual density on the gateway.
