from pathlib import Path

chart_path = Path("ocharts/src/eSENCChart.cpp")
plugin_path = Path("ocharts/src/o-charts_pi.cpp")

chart = chart_path.read_text(encoding="utf-8")
plugin = plugin_path.read_text(encoding="utf-8")


def replace_once(src, old, new, label):
    if old not in src:
        raise SystemExit(
            f"Patch anchor not found: {label}. Upstream source changed."
        )
    return src.replace(old, new, 1)


# LEVEL 1
# Prove that the modified o-charts DLL itself is the DLL OpenCPN loads.
plugin = replace_once(
    plugin,
    """int o_charts_pi::Init(void)
{
    //  Get the path of the PlugIn itself
    g_pi_filename = GetPlugInPath(this);
""",
    """int o_charts_pi::Init(void)
{
    // GEM probe: prove this modified DLL is executing.
    wxLogMessage(_T("GEMPROBE DLL LOADED build=2f54f45"));

    //  Get the path of the PlugIn itself
    g_pi_filename = GetPlugInPath(this);
    wxLogMessage(_T("GEMPROBE DLL PATH: ") + g_pi_filename);
""",
    "plugin Init"
)


# LEVEL 2
# Instrument the ACTIVE GetObjRuleListAtLatLon implementation.
chart = replace_once(
    chart,
    """ListOfPI_S57Obj *eSENCChart::GetObjRuleListAtLatLon(float lat, float lon, float select_radius,
                                                    PlugIn_ViewPort *VPoint)

{
    ViewPort cvp = CreateCompatibleViewport( *VPoint );
""",
    """ListOfPI_S57Obj *eSENCChart::GetObjRuleListAtLatLon(float lat, float lon, float select_radius,
                                                    PlugIn_ViewPort *VPoint)

{
    wxLogMessage("GEMPROBE HITTEST ENTER lat=%.8f lon=%.8f radius=%.8f",
                 lat, lon, select_radius);

    ViewPort cvp = CreateCompatibleViewport( *VPoint );
""",
    "active GetObjRuleListAtLatLon entry"
)

chart = replace_once(
    chart,
    """    obj_list->DeleteContents( true );
    return obj_list;
}

bool isPointInObjectBoundary""",
    """    obj_list->DeleteContents( true );

    wxLogMessage("GEMPROBE HITTEST EXIT objects=%lu",
                 (unsigned long)obj_list->GetCount());

    return obj_list;
}

bool isPointInObjectBoundary""",
    "active GetObjRuleListAtLatLon exit"
)


# LEVEL 3
# Instrument Object Query description generation.
chart = replace_once(
    chart,
    """wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
    wxString ret_val;
""",
    """wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
    wxLogMessage("GEMPROBE DESCRIBE ENTER objects=%lu",
                 (unsigned long)(obj_list ? obj_list->GetCount() : 0));

    wxString ret_val;
""",
    "CreateObjDescriptions entry"
)


# LEVEL 4
# Log only objects already selected by Object Query.
chart = replace_once(
    chart,
    """        className = wxString( current->FeatureName, wxConvUTF8 );

        // Lights get grouped together to make display look nicer.
""",
    """        className = wxString( current->FeatureName, wxConvUTF8 );

        wxLogMessage("GEMQUERY BEGIN feature=%s index=%d",
                     className.c_str(), current->Index);

        // Lights get grouped together to make display look nicer.
""",
    "object begin"
)

chart = replace_once(
    chart,
    """                positionString += toSDMM_PlugIn( 2, lon );


                if( isLight ) {
""",
    """                positionString += toSDMM_PlugIn( 2, lon );

                wxLogMessage("GEMQUERY POSITION feature=%s lat=%.8f lon=%.8f display=%s",
                             className.c_str(), lat, lon,
                             positionString.c_str());

                if( isLight ) {
""",
    "position"
)

chart = replace_once(
    chart,
    """                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( isLight ) {
""",
    """                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    wxLogMessage("GEMQUERY ATTR feature=%s name=%s value=%s",
                                 className.c_str(),
                                 curAttrName.c_str(),
                                 value.c_str());

                    if( isLight ) {
""",
    "attribute"
)


chart_path.write_text(chart, encoding="utf-8")
plugin_path.write_text(plugin, encoding="utf-8")

print("Patched", plugin_path)
print("Patched", chart_path)
print(
    "GEM probe levels: DLL load -> hit-test -> description -> selected attributes"
)
