# GEM OpenCPN Bridge

Experimental OpenCPN bridge for the GEM Marine SMS.

## GEM Test 0.01

This proof-of-concept requests OpenCPN's `WANTS_VECTOR_CHART_OBJECT_INFO` callback and writes the object information supplied by OpenCPN to `opencpn.log`.

Initial test target: **South Kent** lateral buoy from the oeSENC British Isles 2026 chart set.

Expected fields: chart, feature, object name, latitude/longitude, display scale and native chart scale.

There is no network access, GEM/Supabase connection or direct access to `.oesu` chart files.

Target: OpenCPN 5.14.0 Windows x86.
