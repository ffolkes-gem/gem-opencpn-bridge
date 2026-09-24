from pathlib import Path

chart_path = Path("ocharts/src/eSENCChart.cpp")
chart = chart_path.read_text(encoding="utf-8")


def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(f"Patch anchor not found: {label}. Upstream source changed.")
    return src.replace(old, new, 1)


# ------------------------------------------------------------
# GEM +11
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

// +10 diagnostic state.  The viewport is COPIED, not retained as a pointer.
static bool g_gemHaveQuery = false;
static bool g_gemInternalScan = false;
static float g_gemQueryLat = 0.0f;
static float g_gemQueryLon = 0.0f;
static float g_gemQueryRadius = 0.0f;
static PlugIn_ViewPort g_gemQueryVP;


ListOfPI_S57Obj *eSENCChart::GetObjRuleListAtLatLon(float lat, float lon, float select_radius,
                                                    PlugIn_ViewPort *VPoint)

{
    // Only remember the real OpenCPN query.  Internal +10 sample calls must
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

# +9 marker and existing selected-object exporter setup.
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


    // --------------------------------------------------------
    // +11 ROUTE-SHAPED DIAGNOSTIC
    //
    // Reads:
    //   <OpenCPN user data>/gem-route-query.json
    //
    // Hard limits:
    //   exactly 2 route points
    //   maximum route length 1000 m
    //   100 m along-track spacing
    //   cross-track offsets -50 / 0 / +50 m
    //
    // Writes:
    //   <OpenCPN user data>/gem-route-test.json
    //
    // Triggered only when CreateObjDescriptions() is reached by a
    // normal Object Query. This remains a deliberately bounded proof.
    // --------------------------------------------------------

    {
        wxString routeInputPath =
            gemDir + wxFILE_SEP_PATH + _T("gem-route-query.json");

        if( wxFileExists(routeInputPath) ) {

            wxFFile routeInput(routeInputPath, _T("rb"));
            wxString routeText;

            if( routeInput.IsOpened() ) {
                routeInput.ReadAll(&routeText, wxConvUTF8);
                routeInput.Close();
            }

            // Deliberately tiny parser for the fixed diagnostic format.
            // Extract the first four numeric values following "lat"/"lon".
            double routeLat[2] = {0.0, 0.0};
            double routeLon[2] = {0.0, 0.0};
            int routePointCount = 0;

            size_t scanPos = 0;

            while( routePointCount < 2 ) {
                int latPos = routeText.find(_T("\"lat\""), scanPos);
                if( latPos == wxNOT_FOUND ) break;

                int latColon = routeText.find(_T(":"), latPos);
                int lonPos = routeText.find(_T("\"lon\""), latColon);
                if( latColon == wxNOT_FOUND || lonPos == wxNOT_FOUND ) break;

                int lonColon = routeText.find(_T(":"), lonPos);
                if( lonColon == wxNOT_FOUND ) break;

                wxString latTail = routeText.Mid(latColon + 1);
                wxString lonTail = routeText.Mid(lonColon + 1);

                double la = 0.0, lo = 0.0;

                if( !latTail.ToDouble(&la) ) {
                    wxString token = latTail.BeforeFirst(',');
                    token.Trim(true).Trim(false);
                    if( !token.ToDouble(&la) ) break;
                }

                wxString lonToken = lonTail.BeforeFirst('}');
                lonToken.Trim(true).Trim(false);
                if( !lonToken.ToDouble(&lo) ) {
                    lonToken = lonTail.BeforeFirst(',');
                    lonToken.Trim(true).Trim(false);
                    if( !lonToken.ToDouble(&lo) ) break;
                }

                routeLat[routePointCount] = la;
                routeLon[routePointCount] = lo;
                routePointCount++;
                scanPos = lonColon + 1;
            }

            if( routePointCount == 2 ) {

                const double pi11 = 3.14159265358979323846;
                const double meanLat =
                    (routeLat[0] + routeLat[1]) * 0.5;

                const double metresPerDegLat11 = 111320.0;
                const double metresPerDegLon11 =
                    111320.0 * cos(meanLat * pi11 / 180.0);

                const double dNorth =
                    (routeLat[1] - routeLat[0]) * metresPerDegLat11;
                const double dEast =
                    (routeLon[1] - routeLon[0]) * metresPerDegLon11;

                const double routeLength =
                    sqrt((dNorth * dNorth) + (dEast * dEast));

                if( routeLength > 0.1 && routeLength <= 1000.0 ) {

                    // Unit vector along route and perpendicular to route.
                    const double uEast = dEast / routeLength;
                    const double uNorth = dNorth / routeLength;
                    const double pEast = -uNorth;
                    const double pNorth = uEast;

                    const double alongSpacing = 100.0;
                    const double crossOffsets[3] = {-50.0, 0.0, 50.0};

                    int alongSteps =
                        (int)ceil(routeLength / alongSpacing);

                    if( alongSteps < 1 ) alongSteps = 1;

                    struct GEMRouteHit {
                        wxString feature;
                        int index;
                        double lat;
                        double lon;
                        bool hasPosition;
                        unsigned long hits;
                        bool enriched;
                    };

                    std::map<wxString, GEMRouteHit> routeHits;
                    unsigned long routeSamples = 0;

                    g_gemInternalScan = true;

                    // First pass: route corridor.
                    for( int step = 0; step <= alongSteps; ++step ) {

                        double along =
                            (step == alongSteps)
                                ? routeLength
                                : step * alongSpacing;

                        if( along > routeLength )
                            along = routeLength;

                        double baseEast = uEast * along;
                        double baseNorth = uNorth * along;

                        for( int ci = 0; ci < 3; ++ci ) {

                            double sampleEast =
                                baseEast + (pEast * crossOffsets[ci]);

                            double sampleNorth =
                                baseNorth + (pNorth * crossOffsets[ci]);

                            float sampleLat =
                                (float)(
                                    routeLat[0] +
                                    sampleNorth / metresPerDegLat11
                                );

                            float sampleLon =
                                (float)(
                                    routeLon[0] +
                                    sampleEast / metresPerDegLon11
                                );

                            ListOfPI_S57Obj *routeObjects =
                                GetObjRuleListAtLatLon(
                                    sampleLat,
                                    sampleLon,
                                    g_gemQueryRadius,
                                    &g_gemQueryVP
                                );

                            routeSamples++;

                            if( routeObjects ) {

                                for(
                                    ListOfPI_S57Obj::Node *rn =
                                        routeObjects->GetFirst();
                                    rn;
                                    rn = rn->GetNext()
                                ) {
                                    PI_S57Obj *ro = rn->GetData();

                                    wxString feature(
                                        ro->FeatureName,
                                        wxConvUTF8
                                    );

                                    wxString key =
                                        feature +
                                        wxString::Format(
                                            _T(":%d"),
                                            ro->Index
                                        );

                                    std::map<wxString, GEMRouteHit>::iterator hitIt =
                                        routeHits.find(key);

                                    if( hitIt == routeHits.end() ) {

                                        GEMRouteHit h;
                                        h.feature = feature;
                                        h.index = ro->Index;
                                        h.lat = 0.0;
                                        h.lon = 0.0;
                                        h.hasPosition = false;
                                        h.hits = 1;
                                        h.enriched = false;

                                        if( ro->npt == 1 ) {
                                            double olon, olat;

                                            fromSM_Plugin(
                                                (ro->x * ro->x_rate) +
                                                    ro->x_origin,
                                                (ro->y * ro->y_rate) +
                                                    ro->y_origin,
                                                m_ref_lat,
                                                m_ref_lon,
                                                &olat,
                                                &olon
                                            );

                                            if( olon > 180.0 )
                                                olon -= 360.0;

                                            h.lat = olat;
                                            h.lon = olon;
                                            h.hasPosition = true;
                                        }

                                        routeHits[key] = h;
                                    }
                                    else {
                                        hitIt->second.hits++;
                                    }
                                }

                                delete routeObjects;
                            }
                        }
                    }

                    // Second pass: exact-position enrichment for point
                    // navigation marks discovered by the corridor.
                    //
                    // Snapshot the positions first because enrichment may
                    // add new objects to routeHits.
                    struct GEMEnrichPoint {
                        double lat;
                        double lon;
                    };

                    std::vector<GEMEnrichPoint> enrichPoints;

                    for(
                        std::map<wxString, GEMRouteHit>::const_iterator it =
                            routeHits.begin();
                        it != routeHits.end();
                        ++it
                    ) {
                        const GEMRouteHit &h = it->second;

                        bool primary =
                            h.feature == _T("BOYLAT") ||
                            h.feature == _T("BOYCAR") ||
                            h.feature == _T("BOYSAW") ||
                            h.feature == _T("BOYISD") ||
                            h.feature == _T("BOYSPP") ||
                            h.feature == _T("BCNLAT") ||
                            h.feature == _T("BCNCAR") ||
                            h.feature == _T("BCNSAW") ||
                            h.feature == _T("BCNSPP");

                        if( primary && h.hasPosition ) {
                            GEMEnrichPoint ep;
                            ep.lat = h.lat;
                            ep.lon = h.lon;
                            enrichPoints.push_back(ep);
                        }
                    }

                    unsigned long enrichmentQueries = 0;

                    for(
                        size_t ei = 0;
                        ei < enrichPoints.size();
                        ++ei
                    ) {
                        ListOfPI_S57Obj *exactObjects =
                            GetObjRuleListAtLatLon(
                                (float)enrichPoints[ei].lat,
                                (float)enrichPoints[ei].lon,
                                g_gemQueryRadius,
                                &g_gemQueryVP
                            );

                        enrichmentQueries++;

                        if( exactObjects ) {
                            for(
                                ListOfPI_S57Obj::Node *en =
                                    exactObjects->GetFirst();
                                en;
                                en = en->GetNext()
                            ) {
                                PI_S57Obj *eo = en->GetData();

                                wxString feature(
                                    eo->FeatureName,
                                    wxConvUTF8
                                );

                                wxString key =
                                    feature +
                                    wxString::Format(
                                        _T(":%d"),
                                        eo->Index
                                    );

                                std::map<wxString, GEMRouteHit>::iterator hitIt =
                                    routeHits.find(key);

                                if( hitIt == routeHits.end() ) {

                                    GEMRouteHit h;
                                    h.feature = feature;
                                    h.index = eo->Index;
                                    h.lat = 0.0;
                                    h.lon = 0.0;
                                    h.hasPosition = false;
                                    h.hits = 0;
                                    h.enriched = true;

                                    if( eo->npt == 1 ) {
                                        double olon, olat;

                                        fromSM_Plugin(
                                            (eo->x * eo->x_rate) +
                                                eo->x_origin,
                                            (eo->y * eo->y_rate) +
                                                eo->y_origin,
                                            m_ref_lat,
                                            m_ref_lon,
                                            &olat,
                                            &olon
                                        );

                                        if( olon > 180.0 )
                                            olon -= 360.0;

                                        h.lat = olat;
                                        h.lon = olon;
                                        h.hasPosition = true;
                                    }

                                    routeHits[key] = h;
                                }
                                else {
                                    hitIt->second.enriched = true;
                                }
                            }

                            delete exactObjects;
                        }
                    }

                    g_gemInternalScan = false;

                    wxString routeJson;

                    routeJson << _T("{\n");
                    routeJson <<
                        _T("  \"gem_format\": \"route-query-test-v1\",\n");

                    routeJson << wxString::Format(
                        _T(
                            "  \"route\": {"
                            "\"start\": {\"latitude\": %.8f, \"longitude\": %.8f}, "
                            "\"end\": {\"latitude\": %.8f, \"longitude\": %.8f}, "
                            "\"length_metres\": %.1f},\n"
                        ),
                        routeLat[0], routeLon[0],
                        routeLat[1], routeLon[1],
                        routeLength
                    );

                    routeJson << wxString::Format(
                        _T(
                            "  \"sampling\": {"
                            "\"along_track_spacing_metres\": 100, "
                            "\"cross_track_offsets_metres\": [-50, 0, 50], "
                            "\"sample_count\": %lu, "
                            "\"enrichment_queries\": %lu},\n"
                        ),
                        routeSamples,
                        enrichmentQueries
                    );

                    routeJson << _T("  \"objects\": [\n");

                    bool firstRouteHit = true;

                    for(
                        std::map<wxString, GEMRouteHit>::const_iterator it =
                            routeHits.begin();
                        it != routeHits.end();
                        ++it
                    ) {
                        const GEMRouteHit &h = it->second;

                        if( !firstRouteHit )
                            routeJson << _T(",\n");

                        routeJson <<
                            _T("    {\"feature\": \"") <<
                            GEMJsonEscape(h.feature) <<
                            _T("\", \"index\": ") <<
                            wxString::Format(
                                _T("%d"),
                                h.index
                            );

                        if( h.hasPosition ) {
                            routeJson << wxString::Format(
                                _T(
                                    ", \"latitude\": %.8f, "
                                    "\"longitude\": %.8f"
                                ),
                                h.lat,
                                h.lon
                            );
                        }

                        routeJson << wxString::Format(
                            _T(
                                ", \"corridor_hits\": %lu, "
                                "\"exact_position_enrichment\": %s}"
                            ),
                            h.hits,
                            h.enriched ? _T("true") : _T("false")
                        );

                        firstRouteHit = false;
                    }

                    routeJson << _T("\n  ],\n");

                    routeJson << wxString::Format(
                        _T("  \"object_count\": %lu\n"),
                        (unsigned long)routeHits.size()
                    );

                    routeJson << _T("}\n");

                    wxString routeOutputPath =
                        gemDir +
                        wxFILE_SEP_PATH +
                        _T("gem-route-test.json");

                    wxFFile routeOutput;

                    if( routeOutput.Open(
                            routeOutputPath,
                            _T("wb")
                        )
                    ) {
                        bool ok =
                            routeOutput.Write(
                                routeJson,
                                wxConvUTF8
                            );

                        routeOutput.Close();

                        wxLogMessage(
                            ok
                                ? _T(
                                    "GEMROUTE +11 WRITE OK "
                                    "objects=%lu samples=%lu enrich=%lu path=%s"
                                )
                                : _T(
                                    "GEMROUTE +11 WRITE FAILED "
                                    "objects=%lu samples=%lu enrich=%lu path=%s"
                                ),
                            (unsigned long)routeHits.size(),
                            routeSamples,
                            enrichmentQueries,
                            routeOutputPath.c_str()
                        );
                    }
                }
                else {
                    wxLogMessage(
                        _T(
                            "GEMROUTE +11 SKIPPED: "
                            "route length %.1f m outside diagnostic limit"
                        ),
                        routeLength
                    );
                }
            }
            else {
                wxLogMessage(
                    _T(
                        "GEMROUTE +11 SKIPPED: "
                        "gem-route-query.json must contain exactly "
                        "two lat/lon route points"
                    )
                );
            }
        }
    }

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
    gemJson << wxString::Format(_T("  \"object_count\": %lu\n"), gemExportedObjects);
    gemJson << _T("}\n");

    wxString gemDir = wxStandardPaths::Get().GetUserDataDir();
    if( !wxDirExists(gemDir) )
        wxFileName::Mkdir(gemDir, wxS_DIR_DEFAULT, wxPATH_MKDIR_FULL);

    wxString gemPath = gemDir + wxFILE_SEP_PATH + _T("gem-selected-object.json");
    wxFFile gemFile;
    if( gemFile.Open(gemPath, _T("wb")) ) {
        bool ok = gemFile.Write(gemJson, wxConvUTF8);
        gemFile.Close();
        wxLogMessage(
            ok ? _T("GEMEXPORT +10 SELECTED WRITE OK objects=%lu path=%s")
               : _T("GEMEXPORT +10 SELECTED WRITE FAILED objects=%lu path=%s"),
            gemExportedObjects, gemPath.c_str()
        );
    }

    // --------------------------------------------------------
    // +10 SMALL DIAGNOSTIC GRID
    // 5x5 points centred on the user's Object Query.
    // Approx 50 m spacing N/S and E/W.
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
        const double cosLat = cos(((double)g_gemQueryLat) * pi / 180.0);
        const double metresPerDegLon =
            (fabs(cosLat) > 0.01) ? (111320.0 * cosLat) : 111320.0;
        const double spacingM = 50.0;

        unsigned long sampleCount = 0;
        g_gemInternalScan = true;

        for( int row = -2; row <= 2; ++row ) {
            for( int col = -2; col <= 2; ++col ) {
                const float sampleLat =
                    (float)(g_gemQueryLat + (row * spacingM / metresPerDegLat));
                const float sampleLon =
                    (float)(g_gemQueryLon + (col * spacingM / metresPerDegLon));

                ListOfPI_S57Obj *sampleObjects =
                    GetObjRuleListAtLatLon(
                        sampleLat,
                        sampleLon,
                        g_gemQueryRadius,
                        &g_gemQueryVP
                    );

                sampleCount++;

                if( sampleObjects ) {
                    for( ListOfPI_S57Obj::Node *gn = sampleObjects->GetFirst();
                         gn; gn = gn->GetNext() ) {
                        PI_S57Obj *go = gn->GetData();
                        wxString feature(go->FeatureName, wxConvUTF8);
                        wxString key = feature +
                            wxString::Format(_T(":%d"), go->Index);

                        std::map<wxString, GEMHit>::iterator it = gemHits.find(key);
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
                                    (go->x * go->x_rate) + go->x_origin,
                                    (go->y * go->y_rate) + go->y_origin,
                                    m_ref_lat, m_ref_lon,
                                    &olat, &olon
                                );
                                if( olon > 180.0 ) olon -= 360.0;
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

                    // GetObjRuleListAtLatLon() sets DeleteContents(true).
                    delete sampleObjects;
                }
            }
        }

        g_gemInternalScan = false;

        wxString corridor;
        corridor << _T("{\n");
        corridor << _T("  \"gem_format\": \"corridor-query-test-v1\",\n");
        corridor << wxString::Format(
            _T("  \"trigger\": {\"latitude\": %.8f, \"longitude\": %.8f},\n"),
            (double)g_gemQueryLat, (double)g_gemQueryLon
        );
        corridor << wxString::Format(
            _T("  \"grid\": {\"rows\": 5, \"columns\": 5, \"spacing_metres\": 50, \"sample_count\": %lu},\n"),
            sampleCount
        );
        corridor << _T("  \"objects\": [\n");

        bool firstHit = true;
        for( std::map<wxString, GEMHit>::const_iterator it = gemHits.begin();
             it != gemHits.end(); ++it ) {
            const GEMHit &h = it->second;
            if( !firstHit ) corridor << _T(",\n");

            corridor << _T("    {\"feature\": \"")
                     << GEMJsonEscape(h.feature)
                     << _T("\", \"index\": ")
                     << wxString::Format(_T("%d"), h.index);

            if( h.hasPosition ) {
                corridor << wxString::Format(
                    _T(", \"latitude\": %.8f, \"longitude\": %.8f"),
                    h.lat, h.lon
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
            gemDir + wxFILE_SEP_PATH + _T("gem-corridor-test.json");

        wxFFile corridorFile;
        if( corridorFile.Open(corridorPath, _T("wb")) ) {
            bool ok = corridorFile.Write(corridor, wxConvUTF8);
            corridorFile.Close();
            wxLogMessage(
                ok ? _T("GEMCORRIDOR +10 WRITE OK objects=%lu samples=%lu path=%s")
                   : _T("GEMCORRIDOR +10 WRITE FAILED objects=%lu samples=%lu path=%s"),
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

chart_path.write_text(chart, encoding="utf-8")

print("Patched", chart_path)
print("GEM +11: +9 selected-object export retained")
print("GEM +11: +10 corridor diagnostic retained")
print("GEM +11: bounded 2-point route diagnostic -> gem-route-test.json")
