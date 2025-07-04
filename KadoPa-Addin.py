"""アルミ角パイプ作成アドイン"""

import traceback
import adsk.core
import adsk.fusion
import json
import os

app = adsk.core.Application.get()
ui = app.userInterface

# グローバル変数でハンドラーを保持
handlers = []
pipes_data = []

def run(context):
    """アドイン開始時に呼ばれる関数"""
    try:
        # JSONファイルからアルミ角パイプ情報を読み込み
        load_pipe_data()
        
        # コマンド定義を作成
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            'KadoPaAddinCmd', 
            'アルミ角パイプ作成', 
            'アルミ角パイプをスケッチに描画します',
            ''
        )
        
        # コマンド作成イベントハンドラーを追加
        on_command_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_command_created)
        handlers.append(on_command_created)
        
        # ツールバーにボタンを追加
        create_panel = ui.allToolbarPanels.itemById('SolidCreatePanel')
        if create_panel:
            create_panel.controls.addCommand(cmd_def)
        
        ui.messageBox('KadoPa アドインが正常に読み込まれました。')
        
    except:
        if ui:
            ui.messageBox(f'アドイン読み込み失敗:\n{traceback.format_exc()}')

def stop(context):
    """アドイン停止時に呼ばれる関数"""
    try:
        # コマンド定義を削除
        cmd_def = ui.commandDefinitions.itemById('KadoPaAddinCmd')
        if cmd_def:
            cmd_def.deleteMe()
        
        # ツールバーからボタンを削除
        create_panel = ui.allToolbarPanels.itemById('SolidCreatePanel')
        if create_panel:
            cmd_control = create_panel.controls.itemById('KadoPaAddinCmd')
            if cmd_control:
                cmd_control.deleteMe()
        
        ui.messageBox('KadoPa アドインが正常に停止されました。')
        
    except:
        if ui:
            ui.messageBox(f'アドイン停止失敗:\n{traceback.format_exc()}')

def load_pipe_data():
    """JSONファイルからパイプデータを読み込み"""
    global pipes_data
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, 'aluminum_pipes.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            pipes_data = json.load(f)
    except:
        pipes_data = [{"width_mm": 10, "height_mm": 10, "thickness_mm": 1}]

class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """コマンド作成時のハンドラー"""
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            
            # プルダウンを作成
            dropdown = inputs.addDropDownCommandInput(
                'pipeSelect', 
                'パイプ選択', 
                adsk.core.DropDownStyles.TextListDropDownStyle
            )
            
            # パイプデータをプルダウンに追加
            for i, pipe in enumerate(pipes_data):
                # 短縮表示
                item_text = f'{pipe["width_mm"]}x{pipe["height_mm"]} t{pipe["thickness_mm"]}'
                dropdown.listItems.add(item_text, i == 0, f'{pipe["width_mm"]}mm x {pipe["height_mm"]}mm t{pipe["thickness_mm"]}')  # 詳細はdescriptionに
            
            # 長さ入力
            length_input = inputs.addValueInput(
                'pipeLength',
                '長さ (mm)',
                'mm',
                adsk.core.ValueInput.createByReal(10.0)  # デフォルト10mm
            )
            # Xオフセット入力
            x_offset_input = inputs.addValueInput(
                'xOffset',
                'Xオフセット (mm)',
                'mm',
                adsk.core.ValueInput.createByReal(0.0)
            )
            # Yオフセット入力
            y_offset_input = inputs.addValueInput(
                'yOffset',
                'Yオフセット (mm)',
                'mm',
                adsk.core.ValueInput.createByReal(0.0)
            )
            
            # 平面選択（任意の平面を選択可能）
            plane_selection = inputs.addSelectionInput(
                'planeSelect',
                'スケッチ平面を選択',
                '平面、面、またはスケッチを選択してください'
            )
            plane_selection.addSelectionFilter('PlanarFaces')
            plane_selection.addSelectionFilter('ConstructionPlanes')
            plane_selection.addSelectionFilter('Sketches')
            plane_selection.setSelectionLimits(1, 1)  # 1つの平面のみ選択
            
            # 原点選択（オプション）
            origin_selection = inputs.addSelectionInput(
                'originSelect',
                '原点を選択（オプション）',
                '頂点、スケッチ点、または作業点を選択してください'
            )
            origin_selection.addSelectionFilter('Vertices')
            origin_selection.addSelectionFilter('SketchPoints')
            origin_selection.setSelectionLimits(0, 1)  # 0または1つの点を選択
            
            # 方向選択（オプション）
            direction_selection = inputs.addSelectionInput(
                'directionSelect',
                '押し出し方向を選択（オプション）',
                'エッジ、軸、またはベクトルを選択してください'
            )
            direction_selection.addSelectionFilter('LinearEdges')
            direction_selection.addSelectionFilter('ConstructionLines')
            direction_selection.setSelectionLimits(0, 1)  # 0または1つの方向を選択
            
            # 実行イベントハンドラーを追加
            on_execute = CommandExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)
            
        except:
            if ui:
                ui.messageBox(f'コマンド作成失敗:\n{traceback.format_exc()}')

class CommandExecuteHandler(adsk.core.CommandEventHandler):
    """コマンド実行時のハンドラー"""
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            
            # 選択されたパイプを取得
            dropdown = inputs.itemById('pipeSelect')
            selected_index = dropdown.selectedItem.index
            pipe = pipes_data[selected_index]
            
            # 長さを取得
            length_input = inputs.itemById('pipeLength')
            length = length_input.value  # cm単位
            
            # 選択された平面を取得
            plane_selection = inputs.itemById('planeSelect')
            if plane_selection.selectionCount == 0:
                ui.messageBox('スケッチ平面を選択してください。')
                return
            selected_plane = plane_selection.selection(0).entity
            
            # 選択された原点を取得（オプション）
            origin_selection = inputs.itemById('originSelect')
            origin_point = None
            if origin_selection.selectionCount > 0:
                origin_entity = origin_selection.selection(0).entity
                if hasattr(origin_entity, 'geometry'):
                    origin_point = origin_entity.geometry
                elif hasattr(origin_entity, 'worldGeometry'):
                    origin_point = origin_entity.worldGeometry
            
            # 選択された方向を取得（オプション）
            direction_selection = inputs.itemById('directionSelect')
            custom_direction = None
            if direction_selection.selectionCount > 0:
                direction_entity = direction_selection.selection(0).entity
                if hasattr(direction_entity, 'geometry'):
                    if hasattr(direction_entity.geometry, 'direction'):
                        custom_direction = direction_entity.geometry.direction
                elif hasattr(direction_entity, 'worldGeometry'):
                    if hasattr(direction_entity.worldGeometry, 'direction'):
                        custom_direction = direction_entity.worldGeometry.direction
            
            width = pipe['width_mm'] / 10  # mm→cm
            height = pipe['height_mm'] / 10  # mm→cm
            
            # アクティブデザインを取得
            product = app.activeProduct
            design = adsk.fusion.Design.cast(product)
            if not design:
                ui.messageBox('Fusionデザインがアクティブではありません。')
                return
            rootComp = design.rootComponent
            
            # 新しいコンポーネントを作成
            pipe_name = f'アルミ角パイプ_{pipe["width_mm"]}x{pipe["height_mm"]}_t{pipe["thickness_mm"]}_L{length*10:.0f}mm'
            occurrence = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occurrence.component.name = pipe_name
            component = occurrence.component
            
            # 選択された平面でスケッチを作成
            sketches = component.sketches
            sketch = sketches.add(selected_plane)
            
            # 角パイプの断面を描画（中空の四角形）
            lines = sketch.sketchCurves.sketchLines
            thickness = pipe['thickness_mm'] / 10  # mm→cm
            
            # 原点を設定（選択された原点または0,0,0）
            x_offset_input = inputs.itemById('xOffset')
            y_offset_input = inputs.itemById('yOffset')
            x_offset = x_offset_input.value if x_offset_input else 0.0
            y_offset = y_offset_input.value if y_offset_input else 0.0
            if origin_point:
                # 選択された点をスケッチ座標系に変換
                sketch_origin = sketch.modelToSketchSpace(origin_point)
                base_x = sketch_origin.x + x_offset / 10  # mm→cm
                base_y = sketch_origin.y + y_offset / 10
            else:
                base_x = x_offset / 10  # mm→cm
                base_y = y_offset / 10
            
            # 外側の四角形
            p0 = adsk.core.Point3D.create(base_x, base_y, 0)
            p1 = adsk.core.Point3D.create(base_x + width, base_y, 0)
            p2 = adsk.core.Point3D.create(base_x + width, base_y + height, 0)
            p3 = adsk.core.Point3D.create(base_x, base_y + height, 0)
            lines.addByTwoPoints(p0, p1)
            lines.addByTwoPoints(p1, p2)
            lines.addByTwoPoints(p2, p3)
            lines.addByTwoPoints(p3, p0)
            
            # 内側の四角形（中空部分）
            inner_width = width - 2 * thickness
            inner_height = height - 2 * thickness
            if inner_width > 0 and inner_height > 0:
                ip0 = adsk.core.Point3D.create(base_x + thickness, base_y + thickness, 0)
                ip1 = adsk.core.Point3D.create(base_x + width - thickness, base_y + thickness, 0)
                ip2 = adsk.core.Point3D.create(base_x + width - thickness, base_y + height - thickness, 0)
                ip3 = adsk.core.Point3D.create(base_x + thickness, base_y + height - thickness, 0)
                lines.addByTwoPoints(ip0, ip1)
                lines.addByTwoPoints(ip1, ip2)
                lines.addByTwoPoints(ip2, ip3)
                lines.addByTwoPoints(ip3, ip0)
            
            # プロファイルを取得して押し出し
            profiles = sketch.profiles
            if profiles.count > 0:
                profile = profiles.item(0)
                if profiles.count > 1:
                    # 中空の場合は外側と内側を含むプロファイルを使用
                    for i in range(profiles.count):
                        prof = profiles.item(i)
                        if prof.profileLoops.count > 1:  # 外側＋内側ループ
                            profile = prof
                            break
                
                # 押し出しフィーチャーを作成
                extrudes = component.features.extrudeFeatures
                ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                
                # 押し出し方向と距離を設定
                if custom_direction:
                    # カスタム方向が指定された場合
                    extent = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(length))
                    ext_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
                    ext_input.direction = custom_direction
                else:
                    # デフォルトの法線方向
                    distance = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(length))
                    ext_input.setOneSideExtent(distance, adsk.fusion.ExtentDirections.PositiveExtentDirection)
                
                extrude = extrudes.add(ext_input)
            
            ui.messageBox(f'{pipe["width_mm"]}mm x {pipe["height_mm"]}mm t{pipe["thickness_mm"]} 長さ{length*10:.0f}mm のアルミ角パイプを作成しました。')
            
        except:
            if ui:
                ui.messageBox(f'実行失敗:\n{traceback.format_exc()}')
