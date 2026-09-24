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
# GEM +8
# Object Query -> direct local file-write proof
#
# Purpose:
#   Prove that code executing inside CreateObjDescriptions()
#   can write a file to the OpenCPN user-data directory.
#
# This deliberately does NOT attempt full JSON export yet.
# ------------------------------------------------------------


# ------------------------------------------------------------
# 1. Add wxWidgets file/path support.
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 2. Mark entry into CreateObjDescriptions().
#
# This gives us an unmistakable +8 marker and confirms that
# the installed DLL really is the +8 build.
# ------------------------------------------------------------

chart = replace_once(
    chart,
    """wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
""",
    """wxString eSENCChart::CreateObjDescriptions( ListOfPI_S57Obj* obj_list )
{
    wxLogMessage(
        _T("GEMPROBE +8 JSON TEST ENTER objects=%lu"),
        (unsigned long)obj_list->GetCount()
    );
""",
    "CreateObjDescriptions +8 marker"
)


# ------------------------------------------------------------
# 3. Write a tiny JSON file from inside the proven attribute
#    processing path.
#
# We trigger on OBJNAM because South Kent has:
#
#       OBJNAM = South Kent
#
# This is deliberately located immediately after
# GetObjectAttributeValueAsString(), which we already know
# executes successfully during Object Query.
# ------------------------------------------------------------

chart = replace_once(
    chart,
    """                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    if( isLight ) {
""",
    r"""                    value = GetObjectAttributeValueAsString( current, attrCounter, curAttrName );

                    // ------------------------------------------------
                    // GEM +8 direct file-write proof.
                    //
                    // Only write when processing OBJNAM so that an
                    // ordinary South Kent Object Query gives us one
                    // simple, deterministic test.
                    // ------------------------------------------------
                    if( curAttrName == _T("OBJNAM") ) {

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
                            _T("gem-export-test.json");

                        wxLogMessage(
                            _T("GEMEXPORT +8 ATTEMPT feature=%s name=%s"),
                            className.c_str(),
                            value.c_str()
                        );

                        wxLogMessage(
                            _T("GEMEXPORT +8 PATH=%s"),
                            gemPath.c_str()
                        );

                        wxString gemTestJson;

                        gemTestJson << _T("{\n");
                        gemTestJson << _T("  \"gem_test\": true,\n");
                        gemTestJson << _T("  \"feature\": \"")
                                    << className
                                    << _T("\",\n");
                        gemTestJson << _T("  \"name\": \"")
                                    << value
                                    << _T("\"\n");
                        gemTestJson << _T("}\n");

                        wxFFile gemFile;

                        if( gemFile.Open(gemPath, _T("wb")) ) {

                            bool gemWriteOK =
                                gemFile.Write(
                                    gemTestJson,
                                    wxConvUTF8
                                );

                            gemFile.Close();

                            if( gemWriteOK ) {
                                wxLogMessage(
                                    _T("GEMEXPORT +8 WRITE OK path=%s"),
                                    gemPath.c_str()
                                );
                            }
                            else {
                                wxLogMessage(
                                    _T("GEMEXPORT +8 WRITE FAILED path=%s"),
                                    gemPath.c_str()
                                );
                            }
                        }
                        else {
                            wxLogMessage(
                                _T("GEMEXPORT +8 OPEN FAILED path=%s"),
                                gemPath.c_str()
                            );
                        }
                    }

                    if( isLight ) {
""",
    "direct file-write proof"
)


chart_path.write_text(chart, encoding="utf-8")

print("Patched", chart_path)
print("GEM +8: Object Query -> direct wxFFile JSON proof")
