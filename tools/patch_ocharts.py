from pathlib import Path

chart_path = Path("ocharts/src/eSENCChart.cpp")
chart = chart_path.read_text(encoding="utf-8")


def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(
            f"Patch anchor not found: {label}. Upstream source changed."
        )
    return src.replace(old, new, 1)


# ------------------------------------------------------------
# GEM +7
# Object Query -> local structured JSON proof
# ------------------------------------------------------------

# Add <fstream> for writing the JSON file.
chart = replace_once(
    chart,
    """#include <unordered_map>
""",
    """#include <unordered_map>
#include <fstream>
""",
    "fstream include"
)


# Add a small JSON escaping helper immediately before
# CreateObjDescriptions().
chart = replace_once(
    chart,
    """wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
""",
    r"""static wxString GEMJsonEscape(const wxString &input)
{
    wxString s = input;
    s.Replace(_T("\\"), _T("\\\\"));
    s.Replace(_T("\""), _T("\\\""));
    s.Replace(_T("\r"), _T("\\r"));
    s.Replace(_T("\n"), _T("\\n"));
    s.Replace(_T("\t"), _T("\\t"));
    return s;
}


wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
""",
    "JSON escape helper"
)


# Initialise the GEM export document when Object Query is invoked.
chart = replace_once(
    chart,
    """    PI_S57Light* curLight = NULL;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    """    PI_S57Light* curLight = NULL;

    wxString gemJson;
    gemJson << _T("{\\n");
    gemJson << _T("  \\"gem_format\\": \\"navigation-object-selection-v1\\",\\n");
    gemJson << _T("  \\"objects\\": [\\n");
    bool gemFirstObject = true;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    "JSON document start"
)


# Create per-object export state.
chart = replace_once(
    chart,
    """        className = wxString( current->FeatureName, wxConvUTF8 );

        // Lights get grouped together to make display look nicer.
""",
    """        className = wxString( current->FeatureName, wxConvUTF8 );

        double gemLat = 0.0;
        double gemLon = 0.0;
        bool gemHasPosition = false;
        wxString gemAttributes;
        bool gemFirstAttribute = true;

        // Lights get grouped together to make display look nicer.
""",
    "per-object state"
)


# Capture the decoded point position.
chart = replace_once(
    chart,
    """                if( lon > 180.0 ) lon -= 360.;

                positionString.Clear();
""",
    """                if( lon > 180.0 ) lon -= 360.;

                gemLat = lat;
                gemLon = lon;
                gemHasPosition = true;

                positionString.Clear();
""",
    "position capture"
)


# Capture each decoded S-57 attribute BEFORE the existing display
# formatting changes it.
chart = replace_once(
    chart,
    """                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( isLight ) {
""",
    """                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( !gemFirstAttribute )
                        gemAttributes << _T(",\\n");

                    gemAttributes << _T("        \\"")
                                  << GEMJsonEscape(curAttrName)
                                  << _T("\\": \\"")
                                  << GEMJsonEscape(value)
                                  << _T("\\"");

                    gemFirstAttribute = false;

                    if( isLight ) {
""",
    "attribute capture"
)


# At the end of each selected object, append its structured record.
chart = replace_once(
    chart,
    """            }
    } // Object for loop
""",
    """            }

        if( !gemFirstObject )
            gemJson << _T(",\\n");

        gemJson << _T("    {\\n");
        gemJson << _T("      \\"feature\\": \\"")
                << GEMJsonEscape(className)
                << _T("\\"");

        if( gemHasPosition ) {
            gemJson << wxString::Format(
                _T(",\\n      \\"latitude\\": %.8f,\\n      \\"longitude\\": %.8f"),
                gemLat, gemLon
            );
        }

        gemJson << _T(",\\n      \\"attributes\\": {");

        if( !gemFirstAttribute )
            gemJson << _T("\\n") << gemAttributes << _T("\\n      ");

        gemJson << _T("}\\n");
        gemJson << _T("    }");

        gemFirstObject = false;

    } // Object for loop

    gemJson << _T("\\n  ]\\n}\\n");

    wxString gemPath =
        wxGetHomeDir() + wxFILE_SEP_PATH + _T("gem-selected-object.json");

    std::ofstream gemFile(
        gemPath.mb_str(wxConvUTF8),
        std::ios::out | std::ios::trunc
    );

    if( gemFile.is_open() ) {
        wxCharBuffer gemUtf8 = gemJson.ToUTF8();

        if( gemUtf8.data() )
            gemFile << gemUtf8.data();

        gemFile.close();

        wxLogMessage(
            _T("GEMEXPORT wrote %lu objects to %s"),
            (unsigned long)obj_list->GetCount(),
            gemPath.c_str()
        );
    }
    else {
        wxLogMessage(
            _T("GEMEXPORT ERROR unable to write %s"),
            gemPath.c_str()
        );
    }
""",
    "JSON object and file output"
)


chart_path.write_text(chart, encoding="utf-8")

print("Patched", chart_path)
print("GEM +7: Object Query -> gem-selected-object.json")
