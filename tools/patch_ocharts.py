from pathlib import Path

chart_path = Path("ocharts/src/eSENCChart.cpp")
chart = chart_path.read_text(encoding="utf-8")


def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(f"Patch anchor not found: {label}. Upstream source changed.")
    return src.replace(old, new, 1)


# ------------------------------------------------------------
# GEM +14 cumulative
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

    // --------------------------------------------------------
    // +11 ROUTE-SHAPED DIAGNOSTIC
    //
    // Reads:
    //   <OpenCPN user data>/gem-route-query.json
    //
    // Hard limits:
    //   2 to 32 route points
    //   maximum total route length 30000 m
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

            // +16: bounded multi-waypoint parser. Accept 2..32
            // {"lat":..., "lon":...} points from the GEM route file.
            double routeLat[32] = {0.0};
            double routeLon[32] = {0.0};
            int routePointCount = 0;

            size_t scanPos = 0;

            while( routePointCount < 32 ) {
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

            if( routePointCount >= 2 ) {

                const double pi11 = 3.14159265358979323846;
                const double metresPerDegLat11 = 111320.0;
                const double alongSpacing = 100.0;
                const double crossOffsets[3] = {-50.0, 0.0, 50.0};

                // Validate and total every leg before scanning.
                double routeLength = 0.0;
                bool routeValid = true;

                for( int leg = 0; leg < routePointCount - 1; ++leg ) {
                    const double meanLat =
                        (routeLat[leg] + routeLat[leg + 1]) * 0.5;
                    const double metresPerDegLon11 =
                        111320.0 * cos(meanLat * pi11 / 180.0);
                    const double dNorth =
                        (routeLat[leg + 1] - routeLat[leg]) *
                        metresPerDegLat11;
                    const double dEast =
                        (routeLon[leg + 1] - routeLon[leg]) *
                        metresPerDegLon11;
                    const double legLength =
                        sqrt((dNorth * dNorth) + (dEast * dEast));

                    if( legLength <= 0.1 ) {
                        routeValid = false;
                        break;
                    }
                    routeLength += legLength;
                }

                if( routeValid && routeLength <= 30000.0 ) {

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

                    struct GEMCandidate {
                        wxString primaryFeature;
                        int primaryIndex;
                        double lat;
                        double lon;
                        wxString name;
                        wxString shape;
                        wxString category;
                        wxString colour;
                        wxString information;
                        wxString sourceDate;
                        wxString sourceIndication;
                        wxArrayString componentFeatures;
                        wxArrayInt componentIndexes;
                        wxArrayString lightColours;
                        wxArrayString lightCharacters;
                        wxArrayString lightGroups;
                        wxArrayString lightPeriods;
                    };

                    std::map<wxString, GEMCandidate> gemCandidates;
                    unsigned long routeSamples = 0;

                    // +17 diagnostic: count returned objects in five route bands.
                    unsigned long gemDiagQueries[5] = {0,0,0,0,0};
                    unsigned long gemDiagObjects[5] = {0,0,0,0,0};

                    g_gemInternalScan = true;

                    // +16 first pass: scan every route leg using the proven
                    // +15 translated viewport. Shared waypoint endpoints are
                    // harmless because routeHits deduplicates feature:index.
                    for( int leg = 0; leg < routePointCount - 1; ++leg ) {

                        const double meanLat =
                            (routeLat[leg] + routeLat[leg + 1]) * 0.5;
                        const double metresPerDegLon11 =
                            111320.0 * cos(meanLat * pi11 / 180.0);
                        const double dNorth =
                            (routeLat[leg + 1] - routeLat[leg]) *
                            metresPerDegLat11;
                        const double dEast =
                            (routeLon[leg + 1] - routeLon[leg]) *
                            metresPerDegLon11;
                        const double legLength =
                            sqrt((dNorth * dNorth) + (dEast * dEast));
                        const double uEast = dEast / legLength;
                        const double uNorth = dNorth / legLength;
                        const double pEast = -uNorth;
                        const double pNorth = uEast;

                        int alongSteps =
                            (int)ceil(legLength / alongSpacing);
                        if( alongSteps < 1 ) alongSteps = 1;

                        for( int step = 0; step <= alongSteps; ++step ) {
                            double along =
                                (step == alongSteps)
                                    ? legLength
                                    : step * alongSpacing;
                            if( along > legLength ) along = legLength;

                            const double baseEast = uEast * along;
                            const double baseNorth = uNorth * along;

                            for( int ci = 0; ci < 3; ++ci ) {
                                const double sampleEast =
                                    baseEast + (pEast * crossOffsets[ci]);
                                const double sampleNorth =
                                    baseNorth + (pNorth * crossOffsets[ci]);

                                const float sampleLat =
                                    (float)(routeLat[leg] +
                                        sampleNorth / metresPerDegLat11);
                                const float sampleLon =
                                    (float)(routeLon[leg] +
                                        sampleEast / metresPerDegLon11);

                                PlugIn_ViewPort routeVP = g_gemQueryVP;
                                const double routeDLat =
                                    sampleLat - routeVP.clat;
                                const double routeDLon =
                                    sampleLon - routeVP.clon;
                                routeVP.clat = sampleLat;
                                routeVP.clon = sampleLon;
                                routeVP.lat_min += routeDLat;
                                routeVP.lat_max += routeDLat;
                                routeVP.lon_min += routeDLon;
                                routeVP.lon_max += routeDLon;

                                ListOfPI_S57Obj *routeObjects =
                                    GetObjRuleListAtLatLon(
                                        sampleLat, sampleLon,
                                        g_gemQueryRadius, &routeVP);

                                routeSamples++;

                                // +17: assign each query to one of five broad
                                // route-position bands. This changes no selection logic.
                                int gemDiagBand = (int)((routeSamples - 1) * 5 / 924);
                                if( gemDiagBand < 0 ) gemDiagBand = 0;
                                if( gemDiagBand > 4 ) gemDiagBand = 4;
                                gemDiagQueries[gemDiagBand]++;
                                if( routeObjects )
                                    gemDiagObjects[gemDiagBand] +=
                                        (unsigned long)routeObjects->GetCount();

                                if( routeObjects ) {
                                    for(
                                        ListOfPI_S57Obj::Node *rn =
                                            routeObjects->GetFirst();
                                        rn;
                                        rn = rn->GetNext()
                                    ) {
                                        PI_S57Obj *ro = rn->GetData();
                                        wxString feature(
                                            ro->FeatureName, wxConvUTF8);
                                        wxString key =
                                            feature + wxString::Format(
                                                _T(":%d"), ro->Index);

                                        std::map<wxString, GEMRouteHit>::iterator
                                            hitIt = routeHits.find(key);

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
                                                    m_ref_lat, m_ref_lon,
                                                    &olat, &olon);
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
                        // +14: centre a copied viewport on the discovered
                        // mark before the exact-position component query.
                        PlugIn_ViewPort enrichVP = g_gemQueryVP;
                        const double enrichDLat =
                            enrichPoints[ei].lat - enrichVP.clat;
                        const double enrichDLon =
                            enrichPoints[ei].lon - enrichVP.clon;
                        enrichVP.clat = enrichPoints[ei].lat;
                        enrichVP.clon = enrichPoints[ei].lon;
                        enrichVP.lat_min += enrichDLat;
                        enrichVP.lat_max += enrichDLat;
                        enrichVP.lon_min += enrichDLon;
                        enrichVP.lon_max += enrichDLon;

                        ListOfPI_S57Obj *exactObjects =
                            GetObjRuleListAtLatLon(
                                (float)enrichPoints[ei].lat,
                                (float)enrichPoints[ei].lon,
                                g_gemQueryRadius,
                                &enrichVP
                            );

                        enrichmentQueries++;

                        if( exactObjects ) {

                            // Build one logical GEM candidate for the primary
                            // buoy/beacon which caused this enrichment query.
                            wxString candidateKey = wxString::Format(
                                _T("%.7f:%.7f"),
                                enrichPoints[ei].lat,
                                enrichPoints[ei].lon
                            );

                            GEMCandidate candidate;
                            candidate.primaryFeature = _T("");
                            candidate.primaryIndex = -1;
                            candidate.lat = enrichPoints[ei].lat;
                            candidate.lon = enrichPoints[ei].lon;

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

                                // Only components at the exact primary-mark
                                // position belong to the logical candidate.
                                bool samePosition = false;
                                double componentLat = 0.0;
                                double componentLon = 0.0;

                                if( eo->npt == 1 ) {
                                    fromSM_Plugin(
                                        (eo->x * eo->x_rate) + eo->x_origin,
                                        (eo->y * eo->y_rate) + eo->y_origin,
                                        m_ref_lat,
                                        m_ref_lon,
                                        &componentLat,
                                        &componentLon
                                    );

                                    if( componentLon > 180.0 )
                                        componentLon -= 360.0;

                                    const double dLat =
                                        fabs(componentLat - enrichPoints[ei].lat);
                                    const double dLon =
                                        fabs(componentLon - enrichPoints[ei].lon);

                                    samePosition =
                                        dLat < 0.000002 &&
                                        dLon < 0.000002;
                                }

                                if( samePosition ) {
                                    bool componentAlreadyAdded = false;

                                    for( size_t ci = 0;
                                         ci < candidate.componentFeatures.GetCount();
                                         ++ci ) {
                                        if( candidate.componentFeatures[ci] == feature &&
                                            candidate.componentIndexes[ci] == eo->Index ) {
                                            componentAlreadyAdded = true;
                                            break;
                                        }
                                    }

                                    if( !componentAlreadyAdded ) {
                                        candidate.componentFeatures.Add(feature);
                                        candidate.componentIndexes.Add(eo->Index);
                                    }

                                    bool isPrimary =
                                        feature == _T("BOYLAT") ||
                                        feature == _T("BOYCAR") ||
                                        feature == _T("BOYSAW") ||
                                        feature == _T("BOYISD") ||
                                        feature == _T("BOYSPP") ||
                                        feature == _T("BCNLAT") ||
                                        feature == _T("BCNCAR") ||
                                        feature == _T("BCNSAW") ||
                                        feature == _T("BCNSPP");

                                    if( isPrimary ) {
                                        candidate.primaryFeature = feature;
                                        candidate.primaryIndex = eo->Index;
                                    }

                                    wxString lightColour;
                                    wxString lightCharacter;
                                    wxString lightGroup;
                                    wxString lightPeriod;

                                    for( int ai = 0; ai < eo->n_attr; ++ai ) {
                                        wxString attrName(
                                            eo->att_array + (ai * 6),
                                            wxConvUTF8,
                                            6
                                        );

                                        wxString attrValue =
                                            GetObjectAttributeValueAsString(
                                                eo,
                                                ai,
                                                attrName
                                            );

                                        attrName.Trim(true).Trim(false);

                                        if( isPrimary ) {
                                            if( attrName == _T("OBJNAM") )
                                                candidate.name = attrValue;
                                            else if( attrName == _T("BOYSHP") ||
                                                     attrName == _T("BCNSHP") )
                                                candidate.shape = attrValue;
                                            else if( attrName == _T("CATLAM") ||
                                                     attrName == _T("CATCAM") ||
                                                     attrName == _T("CATSPM") )
                                                candidate.category = attrValue;
                                            else if( attrName == _T("COLOUR") )
                                                candidate.colour = attrValue;
                                            else if( attrName == _T("INFORM") )
                                                candidate.information = attrValue;
                                            else if( attrName == _T("SORDAT") )
                                                candidate.sourceDate = attrValue;
                                            else if( attrName == _T("SORIND") )
                                                candidate.sourceIndication = attrValue;
                                        }

                                        if( feature == _T("LIGHTS") ) {
                                            if( attrName == _T("COLOUR") )
                                                lightColour = attrValue;
                                            else if( attrName == _T("LITCHR") )
                                                lightCharacter = attrValue;
                                            else if( attrName == _T("SIGGRP") )
                                                lightGroup = attrValue;
                                            else if( attrName == _T("SIGPER") )
                                                lightPeriod = attrValue;
                                        }
                                    }

                                    if( feature == _T("LIGHTS") ) {
                                        candidate.lightColours.Add(lightColour);
                                        candidate.lightCharacters.Add(lightCharacter);
                                        candidate.lightGroups.Add(lightGroup);
                                        candidate.lightPeriods.Add(lightPeriod);
                                    }
                                }

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

                            if( !candidate.primaryFeature.IsEmpty() )
                                gemCandidates[candidateKey] = candidate;

                            delete exactObjects;
                        }
                    }

                    g_gemInternalScan = false;

                    wxString routeJson;

                    routeJson << _T("{\n");
                    routeJson <<
                        _T("  \"gem_format\": \"route-query-test-v2\",\n");

                    routeJson << wxString::Format(
                        _T(
                            "  \"route\": {"
                            "\"start\": {\"latitude\": %.8f, \"longitude\": %.8f}, "
                            "\"end\": {\"latitude\": %.8f, \"longitude\": %.8f}, "
                            "\"length_metres\": %.1f},\n"
                        ),
                        routeLat[0], routeLon[0],
                        routeLat[routePointCount - 1],
                        routeLon[routePointCount - 1],
                        routeLength
                    );

                    routeJson << wxString::Format(
                        _T(
                            "  \"sampling\": {"
                            "\"waypoint_count\": %d, "
                            "\"leg_count\": %d, "
                            "\"along_track_spacing_metres\": 100, "
                            "\"cross_track_offsets_metres\": [-50, 0, 50], "
                            "\"sample_count\": %lu, "
                            "\"enrichment_queries\": %lu},\n"
                        ),
                        routePointCount,
                        routePointCount - 1,
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
                                    "GEMROUTE +18 WRITE OK "
                                    "objects=%lu samples=%lu enrich=%lu path=%s"
                                )
                                : _T(
                                    "GEMROUTE +18 WRITE FAILED "
                                    "objects=%lu samples=%lu enrich=%lu path=%s"
                                ),
                            (unsigned long)routeHits.size(),
                            routeSamples,
                            enrichmentQueries,
                            routeOutputPath.c_str()
                        );
                    }

                    // +13 presentation normalization.
                    // Preserve raw decoded S-57 strings and derive clean text/code
                    // separately.  Values without a trailing "(number)" remain text-only.
                    struct GEMNormValue {
                        wxString raw;
                        wxString text;
                        wxString code;
                    };

                    // Local lambda-style helper is avoided for compatibility with
                    // the older Windows build toolchain used by this plugin.
                    #define GEM_NORMALIZE_VALUE(INPUT, OUT)                           \
                        OUT.raw = INPUT;                                               \
                        OUT.text = INPUT;                                              \
                        OUT.code = _T("");                                             \
                        {                                                              \
                            int gemClose = OUT.text.Find(')', true);                   \
                            int gemOpen = OUT.text.Find('(', true);                    \
                            if( gemOpen != wxNOT_FOUND &&                              \
                                gemClose == (int)OUT.text.Length() - 1 &&              \
                                gemOpen < gemClose ) {                                 \
                                wxString gemMaybeCode =                                \
                                    OUT.text.Mid(gemOpen + 1, gemClose - gemOpen - 1); \
                                long gemCodeNumber = 0;                                \
                                if( gemMaybeCode.ToLong(&gemCodeNumber) ) {            \
                                    OUT.code = gemMaybeCode;                           \
                                    OUT.text = OUT.text.Left(gemOpen);                 \
                                    OUT.text.Trim(true).Trim(false);                   \
                                }                                                      \
                            }                                                          \
                        }

                    // +18 viewport/chart-state diagnostic.
                    // Acquisition logic is deliberately unchanged from +17.
                    wxString vpJson;
                    vpJson << _T("{\n");
                    vpJson << _T("  \"gem_format\": \"viewport-diagnostic-v1\",\n");
                    vpJson << _T("  \"scanner_version\": \"GEM +18\",\n");
                    vpJson << wxString::Format(
                        _T("  \"centre\": {\"latitude\": %.8f, \"longitude\": %.8f},\n"),
                        g_gemQueryVP.clat, g_gemQueryVP.clon);
                    vpJson << wxString::Format(
                        _T("  \"bounds\": {\"lat_min\": %.8f, \"lat_max\": %.8f, "
                           "\"lon_min\": %.8f, \"lon_max\": %.8f},\n"),
                        g_gemQueryVP.lat_min, g_gemQueryVP.lat_max,
                        g_gemQueryVP.lon_min, g_gemQueryVP.lon_max);
                    vpJson << wxString::Format(
                        _T("  \"pixel_size\": {\"width\": %d, \"height\": %d},\n"),
                        g_gemQueryVP.pix_width, g_gemQueryVP.pix_height);
                    vpJson << wxString::Format(
                        _T("  \"view_scale_ppm\": %.12g,\n"),
                        g_gemQueryVP.view_scale_ppm);
                    vpJson << wxString::Format(
                        _T("  \"chart_scale\": %.12g,\n"),
                        g_gemQueryVP.chart_scale);
                    vpJson << wxString::Format(
                        _T("  \"rotation_radians\": %.12g,\n"),
                        g_gemQueryVP.rotation);
                    vpJson << wxString::Format(
                        _T("  \"skew_radians\": %.12g,\n"),
                        g_gemQueryVP.skew);
                    vpJson << wxString::Format(
                        _T("  \"route\": {\"length_metres\": %.1f, "
                           "\"waypoint_count\": %d, \"sample_count\": %lu},\n"),
                        routeLength, routePointCount, routeSamples);
                    vpJson << _T("  \"note\": \"Cached viewport from the normal Object Query which seeded the route scan\"\n");
                    vpJson << _T("}\n");

                    wxString vpPath =
                        gemDir + wxFILE_SEP_PATH + _T("gem-viewport-diagnostic.json");
                    wxFFile vpFile;
                    if( vpFile.Open(vpPath, _T("wb")) ) {
                        bool vpOK = vpFile.Write(vpJson, wxConvUTF8);
                        vpFile.Close();
                        wxLogMessage(
                            vpOK
                                ? _T("GEMVIEW +18 WRITE OK path=%s")
                                : _T("GEMVIEW +18 WRITE FAILED path=%s"),
                            vpPath.c_str());
                    }

                    // +17/+18 route-return diagnostic. The existing route and
                    // candidate outputs remain unchanged.
                    wxString diagJson;
                    diagJson << _T("{\n");
                    diagJson << _T("  \"gem_format\": \"route-diagnostic-v1\",\n");
                    diagJson << wxString::Format(
                        _T("  \"route_length_metres\": %.1f,\n"), routeLength);
                    diagJson << wxString::Format(
                        _T("  \"waypoint_count\": %d,\n"), routePointCount);
                    diagJson << _T("  \"bands\": [\n");
                    for( int di = 0; di < 5; ++di ) {
                        if( di ) diagJson << _T(",\n");
                        diagJson << wxString::Format(
                            _T("    {\"band\": %d, \"queries\": %lu, \"returned_objects\": %lu}"),
                            di + 1, gemDiagQueries[di], gemDiagObjects[di]);
                    }
                    diagJson << _T("\n  ]\n}\n");

                    wxString diagPath =
                        gemDir + wxFILE_SEP_PATH + _T("gem-route-diagnostic.json");
                    wxFFile diagFile;
                    if( diagFile.Open(diagPath, _T("wb")) ) {
                        bool diagOK = diagFile.Write(diagJson, wxConvUTF8);
                        diagFile.Close();
                        wxLogMessage(
                            diagOK
                                ? _T("GEMDIAG +18 WRITE OK path=%s")
                                : _T("GEMDIAG +18 WRITE FAILED path=%s"),
                            diagPath.c_str());
                    }

                    wxString candidatesJson;
                    candidatesJson << _T("{\n");
                    candidatesJson << _T("  \"gem_format\": \"route-navigation-candidates-v2\",\n");
                    candidatesJson << _T("  \"candidates\": [\n");

                    bool firstCandidate = true;

                    for(
                        std::map<wxString, GEMCandidate>::const_iterator cit =
                            gemCandidates.begin();
                        cit != gemCandidates.end();
                        ++cit
                    ) {
                        const GEMCandidate &c = cit->second;

                        if( !firstCandidate )
                            candidatesJson << _T(",\n");

                        candidatesJson << _T("    {\n");
                        candidatesJson << _T("      \"name\": \"")
                                       << GEMJsonEscape(c.name)
                                       << _T("\",\n");
                        candidatesJson << _T("      \"primary_feature\": \"")
                                       << GEMJsonEscape(c.primaryFeature)
                                       << _T("\",\n");
                        candidatesJson << wxString::Format(
                            _T("      \"primary_index\": %d,\n"),
                            c.primaryIndex
                        );
                        candidatesJson << wxString::Format(
                            _T("      \"position\": {\"latitude\": %.8f, \"longitude\": %.8f},\n"),
                            c.lat, c.lon
                        );
                        GEMNormValue normShape;
                        GEMNormValue normCategory;
                        GEMNormValue normColour;
                        GEM_NORMALIZE_VALUE(c.shape, normShape);
                        GEM_NORMALIZE_VALUE(c.category, normCategory);
                        GEM_NORMALIZE_VALUE(c.colour, normColour);

                        candidatesJson << _T("      \"shape\": {\"raw\": \"")
                                       << GEMJsonEscape(normShape.raw)
                                       << _T("\", \"text\": \"")
                                       << GEMJsonEscape(normShape.text)
                                       << _T("\", \"code\": \"")
                                       << GEMJsonEscape(normShape.code)
                                       << _T("\"},\n");
                        candidatesJson << _T("      \"category\": {\"raw\": \"")
                                       << GEMJsonEscape(normCategory.raw)
                                       << _T("\", \"text\": \"")
                                       << GEMJsonEscape(normCategory.text)
                                       << _T("\", \"code\": \"")
                                       << GEMJsonEscape(normCategory.code)
                                       << _T("\"},\n");
                        candidatesJson << _T("      \"colour\": {\"raw\": \"")
                                       << GEMJsonEscape(normColour.raw)
                                       << _T("\", \"text\": \"")
                                       << GEMJsonEscape(normColour.text)
                                       << _T("\", \"code\": \"")
                                       << GEMJsonEscape(normColour.code)
                                       << _T("\"},\n");
                        candidatesJson << _T("      \"information\": \"")
                                       << GEMJsonEscape(c.information)
                                       << _T("\",\n");
                        candidatesJson << _T("      \"source\": {\"SORDAT\": \"")
                                       << GEMJsonEscape(c.sourceDate)
                                       << _T("\", \"SORIND\": \"")
                                       << GEMJsonEscape(c.sourceIndication)
                                       << _T("\"},\n");

                        wxString displayLine = normCategory.text;
                        if( !normColour.text.IsEmpty() ) {
                            if( !displayLine.IsEmpty() ) displayLine << _T(" - ");
                            displayLine << normColour.text;
                        }
                        if( !normShape.text.IsEmpty() ) {
                            if( !displayLine.IsEmpty() ) displayLine << _T(" ");
                            displayLine << normShape.text;
                        }

                        candidatesJson << _T("      \"display\": {\"name\": \"")
                                       << GEMJsonEscape(c.name)
                                       << _T("\", \"description\": \"")
                                       << GEMJsonEscape(displayLine)
                                       << _T("\"},\n");

                        candidatesJson << _T("      \"components\": [");
                        for( size_t ci = 0;
                             ci < c.componentFeatures.GetCount();
                             ++ci ) {
                            if( ci ) candidatesJson << _T(", ");
                            candidatesJson << _T("{\"feature\": \"")
                                           << GEMJsonEscape(c.componentFeatures[ci])
                                           << _T("\", \"index\": ")
                                           << wxString::Format(
                                               _T("%d"),
                                               c.componentIndexes[ci]
                                           )
                                           << _T("}");
                        }
                        candidatesJson << _T("],\n");

                        candidatesJson << _T("      \"lights\": [");
                        for( size_t li = 0;
                             li < c.lightCharacters.GetCount();
                             ++li ) {
                            if( li ) candidatesJson << _T(", ");
                            GEMNormValue lightColour;
                            GEMNormValue lightCharacter;
                            GEMNormValue lightGroup;
                            GEMNormValue lightPeriod;
                            GEM_NORMALIZE_VALUE(c.lightColours[li], lightColour);
                            GEM_NORMALIZE_VALUE(c.lightCharacters[li], lightCharacter);
                            GEM_NORMALIZE_VALUE(c.lightGroups[li], lightGroup);
                            GEM_NORMALIZE_VALUE(c.lightPeriods[li], lightPeriod);

                            candidatesJson << _T("{\"colour\": {\"raw\": \"")
                                           << GEMJsonEscape(lightColour.raw)
                                           << _T("\", \"text\": \"")
                                           << GEMJsonEscape(lightColour.text)
                                           << _T("\", \"code\": \"")
                                           << GEMJsonEscape(lightColour.code)
                                           << _T("\"}, \"character\": {\"raw\": \"")
                                           << GEMJsonEscape(lightCharacter.raw)
                                           << _T("\", \"text\": \"")
                                           << GEMJsonEscape(lightCharacter.text)
                                           << _T("\", \"code\": \"")
                                           << GEMJsonEscape(lightCharacter.code)
                                           << _T("\"}, \"group\": \"")
                                           << GEMJsonEscape(lightGroup.raw)
                                           << _T("\", \"period\": \"")
                                           << GEMJsonEscape(lightPeriod.raw)
                                           << _T("\"}");
                        }
                        candidatesJson << _T("]\n");
                        candidatesJson << _T("    }");

                        firstCandidate = false;
                    }

                    candidatesJson << _T("\n  ],\n");
                    candidatesJson << wxString::Format(
                        _T("  \"candidate_count\": %lu\n"),
                        (unsigned long)gemCandidates.size()
                    );
                    candidatesJson << _T("}\n");

                    wxString candidatesPath =
                        gemDir +
                        wxFILE_SEP_PATH +
                        _T("gem-route-candidates-v2.json");

                    wxFFile candidatesFile;

                    if( candidatesFile.Open(candidatesPath, _T("wb")) ) {
                        bool candidatesOK =
                            candidatesFile.Write(
                                candidatesJson,
                                wxConvUTF8
                            );

                        candidatesFile.Close();

                        wxLogMessage(
                            candidatesOK
                                ? _T(
                                    "GEMCANDIDATES +18 WRITE OK "
                                    "candidates=%lu path=%s"
                                )
                                : _T(
                                    "GEMCANDIDATES +18 WRITE FAILED "
                                    "candidates=%lu path=%s"
                                ),
                            (unsigned long)gemCandidates.size(),
                            candidatesPath.c_str()
                        );
                    }

                    #undef GEM_NORMALIZE_VALUE
                }
                else {
                    wxLogMessage(
                        _T(
                            "GEMROUTE +18 SKIPPED: "
                            "route length %.1f m outside diagnostic limit"
                        ),
                        routeLength
                    );
                }
            }
            else {
                wxLogMessage(
                    _T(
                        "GEMROUTE +18 SKIPPED: "
                        "gem-route-query.json must contain 2 to 32 "
                        "lat/lon route points"
                    )
                );
            }
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
print("GEM +18: bounded 2-32 point / 30 km route diagnostic -> gem-route-test.json")
print("GEM +18: normalized/raw navigation candidates -> gem-route-candidates-v2.json")
