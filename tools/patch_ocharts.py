from pathlib import Path
path = Path("ocharts/src/eSENCChart.cpp")
src = path.read_text(encoding="utf-8")

changes = [
("""        className = wxString( current->FeatureName, wxConvUTF8 );

        // Lights get grouped together to make display look nicer.
""",
"""        className = wxString( current->FeatureName, wxConvUTF8 );

        // GEM selected-object probe: only objects already selected by Object Query.
        wxLogMessage("GEMQUERY BEGIN feature=%s index=%d",
                     className.c_str(), current->Index);

        // Lights get grouped together to make display look nicer.
""", "object begin"),

("""                positionString += toSDMM_PlugIn( 2, lon );


                if( isLight ) {
""",
"""                positionString += toSDMM_PlugIn( 2, lon );

                wxLogMessage("GEMQUERY POSITION feature=%s lat=%.8f lon=%.8f display=%s",
                             className.c_str(), lat, lon, positionString.c_str());

                if( isLight ) {
""", "position"),

("""                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( isLight ) {
""",
"""                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    wxLogMessage("GEMQUERY ATTR feature=%s name=%s value=%s",
                                 className.c_str(), curAttrName.c_str(), value.c_str());

                    if( isLight ) {
""", "attribute"),

("""            }
    } // Object for loop
""",
"""            }

            wxLogMessage("GEMQUERY END feature=%s index=%d",
                         className.c_str(), current->Index);
    } // Object for loop
""", "object end"),
]

for old, new, label in changes:
    if old not in src:
        raise SystemExit(f"Patch anchor not found: {label}. Upstream source changed.")
    src = src.replace(old, new, 1)

path.write_text(src, encoding="utf-8")
print("Patched", path)
