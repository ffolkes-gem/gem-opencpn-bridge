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
# GEM +9
# Object Query -> complete structured JSON selection
# ------------------------------------------------------------

# 1. wxWidgets file/path support.
chart = replace_once(
    chart,
    """#include <unordered_map>
""",
    """#include <unordered_map>
#include <wx/ffile.h>
#include <wx/stdpaths.h>
#include <wx/filename.h>
""",
    "wx file includes"
)


# 2. JSON escaping helper + unmistakable +9 marker.
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
    wxLogMessage(
        _T("GEMPROBE +9 JSON EXPORT ENTER objects=%lu"),
        (unsigned long)obj_list->GetCount()
    );
""",
    "CreateObjDescriptions +9 marker"
)


# 3. Start one JSON document for the complete Object Query.
chart = replace_once(
    chart,
    """    PI_S57Light* curLight = NULL;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    r"""    PI_S57Light* curLight = NULL;

    wxString gemJson;
    gemJson << _T("{\n");
    gemJson << _T("  \"gem_format\": \"navigation-object-selection-v1\",\n");
    gemJson << _T("  \"objects\": [\n");

    bool gemFirstObject = true;
    unsigned long gemExportedObjects = 0;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    "JSON document start"
)


# 4. Per-object state.
chart = replace_once(
    chart,
    """        className = wxString( current->FeatureName, wxConvUTF8 );

        // Lights get grouped together to make display look nicer.
""",
    r"""        className = wxString( current->FeatureName, wxConvUTF8 );

        double gemLat = 0.0;
        double gemLon = 0.0;
        bool gemHasPosition = false;
        wxString gemAttributes;
        bool gemFirstAttribute = true;

        // Lights get grouped together to make display look nicer.
""",
    "per-object JSON state"
)


# 5. Preserve decimal WGS84 position for point objects.
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


# 6. Capture every decoded attribute BEFORE existing display
# formatting can modify the value.
chart = replace_once(
    chart,
    """                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( isLight ) {
""",
    r"""                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( !gemFirstAttribute )
                        gemAttributes << _T(",\n");

                    gemAttributes << _T("        \"")
                                  << GEMJsonEscape(curAttrName)
                                  << _T("\": \"")
                                  << GEMJsonEscape(value)
                                  << _T("\"");

                    gemFirstAttribute = false;

                    if( isLight ) {
""",
    "attribute capture"
)


# 7. Append each selected object, then write once after the
# complete Object Query loop has finished.
chart = replace_once(
    chart,
    """            }
    } // Object for loop

    // Add the additional info files
""",
    r"""            }

        if( !gemFirstObject )
            gemJson << _T(",\n");

        gemJson << _T("    {\n");
        gemJson << _T("      \"feature\": \"")
                << GEMJsonEscape(className)
                << _T("\",\n");

        gemJson << wxString::Format(
            _T("      \"index\": %d"),
            current->Index
        );

        if( gemHasPosition ) {
            gemJson << wxString::Format(
                _T(",\n      \"latitude\": %.8f,\n      \"longitude\": %.8f"),
                gemLat,
                gemLon
            );
        }

        gemJson << _T(",\n      \"attributes\": {");

        if( !gemFirstAttribute )
            gemJson << _T("\n") << gemAttributes << _T("\n      ");

        gemJson << _T("}\n");
        gemJson << _T("    }");

        gemFirstObject = false;
        gemExportedObjects++;

    } // Object for loop

    gemJson << _T("\n  ],\n");

    gemJson << wxString::Format(
        _T("  \"object_count\": %lu\n"),
        gemExportedObjects
    );

    gemJson << _T("}\n");


    wxString gemDir =
        wxStandardPaths::Get().GetUserDataDir();

    if( !wxDirExists(gemDir) ) {
        wxFileName::Mkdir(
            gemDir,
            wxS_DIR_DEFAULT,
            wxPATH_MKDIR_FULL
        );
    }

    wxString gemPath =
        gemDir +
        wxFILE_SEP_PATH +
        _T("gem-selected-object.json");

    wxLogMessage(
        _T("GEMEXPORT +9 PATH=%s"),
        gemPath.c_str()
    );

    wxFFile gemFile;

    if( gemFile.Open(gemPath, _T("wb")) ) {

        bool gemWriteOK =
            gemFile.Write(
                gemJson,
                wxConvUTF8
            );

        gemFile.Close();

        if( gemWriteOK ) {
            wxLogMessage(
                _T("GEMEXPORT +9 WRITE OK objects=%lu path=%s"),
                gemExportedObjects,
                gemPath.c_str()
            );
        }
        else {
            wxLogMessage(
                _T("GEMEXPORT +9 WRITE FAILED path=%s"),
                gemPath.c_str()
            );
        }
    }
    else {
        wxLogMessage(
            _T("GEMEXPORT +9 OPEN FAILED path=%s"),
            gemPath.c_str()
        );
    }

    // Add the additional info files
""",
    "JSON object append and single file output"
)


chart_path.write_text(chart, encoding="utf-8")

print("Patched", chart_path)
print("GEM +9: complete Object Query -> gem-selected-object.json")
