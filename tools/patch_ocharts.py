from pathlib import Path

chart_path = Path("ocharts/src/eSENCChart.cpp")
chart = chart_path.read_text(encoding="utf-8")


def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(f"Patch anchor not found: {label}. Upstream source changed.")
    return src.replace(old, new, 1)


# ------------------------------------------------------------
# GEM +10
# Keeps +9 selected-object JSON intact.
# Adds a deliberately small 5x5 diagnostic grid around the
# user's normal Object Query click and writes a deduplicated
# gem-corridor-test.json.
# ------------------------------------------------------------

chart = replace_once(
    chart,
    """#include <unordered_map>
""",
    """#include <unordered_map>
#include <wx/ffile.h>
#include <wx/stdpaths.h>
#include <wx/filename.h>
#include <map>
""",
    "includes"
)

# JSON escaping helper and copied query state.
chart = replace_once(
    chart,
    """ListOfPI_S57Obj *eSENCChart::GetObjRuleListAtLatLon(float lat, float lon, float select_radius,
                                                    PlugIn_ViewPort *VPoint)

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

// +10 diagnostic state. The viewport is COPIED, not retained as a pointer.
static bool g_gemHaveQuery = false;
static bool g_gemInternalScan = false;
static float g_gemQueryLat = 0.0f;
static float g_gemQueryLon = 0.0f;
static float g_gemQueryRadius = 0.0f;
static PlugIn_ViewPort g_gemQueryVP;


ListOfPI_S57Obj *eSENCChart::GetObjRuleListAtLatLon(float lat, float lon, float select_radius,
                                                    PlugIn_ViewPort *VPoint)

{
    // Only remember the real OpenCPN query. Internal +10 sample calls must
    // not replace the trigger coordinate/viewport.
    if( !g_gemInternalScan && VPoint ) {
        g_gemQueryLat = lat;
        g_gemQueryLon = lon;
        g_gemQueryRadius = select_radius;
        g_gemQueryVP = *VPoint;
        g_gemHaveQuery = true;
    }
""",
    "query state capture"
)

# +10 marker and existing selected-object exporter setup.
chart = replace_once(
    chart,
    """wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
""",
    r"""wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
    wxLogMessage(
        _T("GEMPROBE +10 ENTER objects=%lu"),
        (unsigned long)obj_list->GetCount()
    );
""",
    "CreateObjDescriptions marker"
)

chart = replace_once(
    chart,
    """    PI_S57Light* curLight = NULL;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    r"""    PI_S57Light* curLight = NULL;

    // Existing +9 complete Object Query document.
    wxString gemJson;
    gemJson << _T("{\n");
    gemJson << _T("  \"gem_format\": \"navigation-object-selection-v1\",\n");
    gemJson << _T("  \"objects\": [\n");

    bool gemFirstObject = true;
    unsigned long gemExportedObjects = 0;

    for( ListOfPI_S57Obj::Node *node = obj_list->GetLast(); node; node = node->GetPrevious() ) {
""",
    "selected JSON start"
)

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
    "per-object state"
)

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

# Close +9 and add +10 diagnostic immediately after normal object loop.
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
        gemJson << wxString::Format(_T("      \"index\": %d"), current->Index);

        if( gemHasPosition ) {
            gemJson << wxString::Format(
                _T(",\n      \"latitude\": %.8f,\n      \"longitude\": %.8f"),
                gemLat, gemLon
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

    wxString gemDir = wxStandardPaths::Get().GetUserDataDir();

    if( !wxDirExists(gemDir) )
        wxFileName::Mkdir(
            gemDir,
            wxS_DIR_DEFAULT,
            wxPATH_MKDIR_FULL
        );

    wxString gemPath =
        gemDir +
        wxFILE_SEP_PATH +
        _T("gem-selected-object.json");

    wxFFile gemFile;

    if( gemFile.Open(gemPath, _T("wb")) ) {
        bool ok = gemFile.Write(gemJson, wxConvUTF8);
        gemFile.Close();

        wxLogMessage(
            ok
                ? _T("GEMEXPORT +10 SELECTED WRITE OK objects=%lu path=%s")
                : _T("GEMEXPORT +10 SELECTED WRITE FAILED objects=%lu path=%s"),
            gemExportedObjects,
            gemPath.c_str()
        );
    }


    // --------------------------------------------------------
    // +10 SMALL DIAGNOSTIC GRID
    //
    // 5 x 5 points centred on the user's Object Query.
    // Approx 50 m spacing N/S and E/W.
    //
    // This is intentionally a local proof, not a chart sweep.
    // --------------------------------------------------------

    if( g_gemHaveQuery ) {

        struct GEMHit {
            wxString feature;
            int index;
            double lat;
            double lon;
            bool hasPosition;
            unsigned long hits;
        };

        std::map<wxString, GEMHit> gemHits;

        const double metresPerDegLat = 111320.0;
        const double pi = 3.14159265358979323846;

        const double cosLat =
            cos(((double)g_gemQueryLat) * pi / 180.0);

        const double metresPerDegLon =
            (fabs(cosLat) > 0.01)
                ? (111320.0 * cosLat)
                : 111320.0;

        const double spacingM = 50.0;

        unsigned long sampleCount = 0;

        // Prevent our own sample queries from replacing the original
        // Object Query position/viewport.
        g_gemInternalScan = true;

        for( int row = -2; row <= 2; ++row ) {

            for( int col = -2; col <= 2; ++col ) {

                const float sampleLat =
                    (float)(
                        g_gemQueryLat +
                        (row * spacingM / metresPerDegLat)
                    );

                const float sampleLon =
                    (float)(
                        g_gemQueryLon +
                        (col * spacingM / metresPerDegLon)
                    );

                ListOfPI_S57Obj *sampleObjects =
                    GetObjRuleListAtLatLon(
                        sampleLat,
                        sampleLon,
                        g_gemQueryRadius,
                        &g_gemQueryVP
                    );

                sampleCount++;

                if( sampleObjects ) {

                    for(
                        ListOfPI_S57Obj::Node *gn =
                            sampleObjects->GetFirst();
                        gn;
                        gn = gn->GetNext()
                    ) {

                        PI_S57Obj *go = gn->GetData();

                        wxString feature(
                            go->FeatureName,
                            wxConvUTF8
                        );

                        // Deduplicate the same ENC object encountered
                        // at several sample positions.
                        wxString key =
                            feature +
                            wxString::Format(
                                _T(":%d"),
                                go->Index
                            );

                        std::map<wxString, GEMHit>::iterator it =
                            gemHits.find(key);

                        if( it == gemHits.end() ) {

                            GEMHit hit;

                            hit.feature = feature;
                            hit.index = go->Index;
                            hit.lat = 0.0;
                            hit.lon = 0.0;
                            hit.hasPosition = false;
                            hit.hits = 1;

                            if( go->npt == 1 ) {

                                double olon, olat;

                                fromSM_Plugin(
                                    (go->x * go->x_rate) +
                                        go->x_origin,
                                    (go->y * go->y_rate) +
                                        go->y_origin,
                                    m_ref_lat,
                                    m_ref_lon,
                                    &olat,
                                    &olon
                                );

                                if( olon > 180.0 )
                                    olon -= 360.0;

                                hit.lat = olat;
                                hit.lon = olon;
                                hit.hasPosition = true;
                            }

                            gemHits[key] = hit;
                        }
                        else {
                            it->second.hits++;
                        }
                    }

                    // GetObjRuleListAtLatLon() sets
                    // DeleteContents(true), so deleting the list
                    // also cleans up its cloned PI_S57Obj objects.
                    delete sampleObjects;
                }
            }
        }

        g_gemInternalScan = false;


        // Build the +10 diagnostic JSON.

        wxString corridor;

        corridor << _T("{\n");

        corridor <<
            _T("  \"gem_format\": \"corridor-query-test-v1\",\n");

        corridor << wxString::Format(
            _T(
                "  \"trigger\": {"
                "\"latitude\": %.8f, "
                "\"longitude\": %.8f},\n"
            ),
            (double)g_gemQueryLat,
            (double)g_gemQueryLon
        );

        corridor << wxString::Format(
            _T(
                "  \"grid\": {"
                "\"rows\": 5, "
                "\"columns\": 5, "
                "\"spacing_metres\": 50, "
                "\"sample_count\": %lu},\n"
            ),
            sampleCount
        );

        corridor << _T("  \"objects\": [\n");

        bool firstHit = true;

        for(
            std::map<wxString, GEMHit>::const_iterator it =
                gemHits.begin();
            it != gemHits.end();
            ++it
        ) {

            const GEMHit &h = it->second;

            if( !firstHit )
                corridor << _T(",\n");

            corridor <<
                _T("    {\"feature\": \"") <<
                GEMJsonEscape(h.feature) <<
                _T("\", \"index\": ") <<
                wxString::Format(
                    _T("%d"),
                    h.index
                );

            if( h.hasPosition ) {

                corridor << wxString::Format(
                    _T(
                        ", \"latitude\": %.8f, "
                        "\"longitude\": %.8f"
                    ),
                    h.lat,
                    h.lon
                );
            }

            corridor << wxString::Format(
                _T(", \"hits\": %lu}"),
                h.hits
            );

            firstHit = false;
        }

        corridor << _T("\n  ],\n");

        corridor << wxString::Format(
            _T("  \"object_count\": %lu\n"),
            (unsigned long)gemHits.size()
        );

        corridor << _T("}\n");


        wxString corridorPath =
            gemDir +
            wxFILE_SEP_PATH +
            _T("gem-corridor-test.json");

        wxFFile corridorFile;

        if( corridorFile.Open(
                corridorPath,
                _T("wb")
            )
        ) {

            bool ok =
                corridorFile.Write(
                    corridor,
                    wxConvUTF8
                );

            corridorFile.Close();

            wxLogMessage(
                ok
                    ? _T(
                        "GEMCORRIDOR +10 WRITE OK "
                        "objects=%lu samples=%lu path=%s"
                    )
                    : _T(
                        "GEMCORRIDOR +10 WRITE FAILED "
                        "objects=%lu samples=%lu path=%s"
                    ),
                (unsigned long)gemHits.size(),
                sampleCount,
                corridorPath.c_str()
            );
        }
    }

    // Add the additional info files
""",
    "selected export and +10 diagnostic"
)


chart_path.write_text(
    chart,
    encoding="utf-8"
)

print("Patched", chart_path)
print("GEM +10: +9 selected-object export retained")
print(
    "GEM +10: 5x5 local query diagnostic "
    "-> gem-corridor-test.json"
)
