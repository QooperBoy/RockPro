exec(open('register_typelib_user.py',encoding='utf-8').read().replace("['ICApiIronCAD.tlb', 'ICApiFoundation.tlb', '3iICApiIronCADApp.dll', '3iICApiDrawing.dll', '3iICApiCore.dll', '3iICApiBase.dll']","['3iICApiIronCADApp.dll', '3iICApiDrawing.dll', '3iICApiCore.dll', '3iICApiBase.dll', 'ICApiFoundation.tlb', 'ICApiIronCAD.tlb']"))
exec(open('recognize_skeleton.py',encoding='utf-8-sig').read())
