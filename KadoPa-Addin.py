"""アルミ角パイプ作成アドイン"""

import traceback
import adsk.core
import adsk.fusion
import sys, os
# モジュール検索パスにスクリプトディレクトリを追加
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
import data_loader

app = adsk.core.Application.get()
ui = app.userInterface

# グローバル変数でハンドラーを保持
handlers = []

def run(context):
    """アドイン開始時に呼ばれる関数"""
    try:
        # JSONファイルからアルミ角パイプ情報を読み込み
        data_loader.load_pipe_data()
        
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
            for i, pipe in enumerate(data_loader.pipes_data):
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
            # Zオフセット入力（追加）
            z_offset_input = inputs.addValueInput(
                'zOffset',
                'Zオフセット (mm)',
                'mm',
                adsk.core.ValueInput.createByReal(0.0)
            )
            # 回転角度入力（追加）
            rotate_input = inputs.addValueInput(
                'rotateAngle',
                '断面回転角度 (度)',
                'deg',
                adsk.core.ValueInput.createByString('0')
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
            
            # 反転ボタン（追加）
            reverse_input = inputs.addBoolValueInput(
                'reverseDirection',
                '反転',
                False,
                '',
                False
            )
            
            # 実行イベントハンドラーを追加
            on_execute = CommandExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)
            # プレビューイベントハンドラーを追加
            on_preview = CommandExecuteHandler()
            cmd.executePreview.add(on_preview)
            handlers.append(on_preview)
            
        except:
            if ui:
                ui.messageBox(f'コマンド作成失敗:\n{traceback.format_exc()}')

class CommandExecuteHandler(adsk.core.CommandEventHandler):
    """コマンド実行時のハンドラー（プレビューと本実行を区別）"""
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs
            
            # 選択されたパイプを取得
            dropdown = inputs.itemById('pipeSelect')
            selected_index = dropdown.selectedItem.index
            pipe = data_loader.pipes_data[selected_index]
            
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
            
            width = pipe['width_mm'] / 10  # mm→cm
            height = pipe['height_mm'] / 10  # mm→cm
            
            # アクティブデザインを取得
            product = app.activeProduct
            design = adsk.fusion.Design.cast(product)
            if not design:
                ui.messageBox('Fusionデザインがアクティブではありません。')
                return
            rootComp = design.rootComponent

            # タイムライングループ開始
            timeline = design.timeline
            group_start = timeline.markerPosition
            
            # 新しいコンポーネントを作成
            pipe_name = f'アルミ角パイプ_{pipe["width_mm"]}x{pipe["height_mm"]}_t{pipe["thickness_mm"]}_L{length*10:.0f}mm'
            occurrence = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occurrence.component.name = pipe_name
            component = occurrence.component
            
            # スケッチ平面のZ方向オフセット
            x_offset_input = inputs.itemById('xOffset')
            y_offset_input = inputs.itemById('yOffset')
            z_offset_input = inputs.itemById('zOffset')  # 追加
            x_offset = x_offset_input.value if x_offset_input else 0.0
            y_offset = y_offset_input.value if y_offset_input else 0.0
            z_offset = z_offset_input.value if z_offset_input else 0.0
            if abs(z_offset) > 1e-6:
                # 選択平面からz_offset分だけオフセットしたコンストラクション平面を作成
                planes = component.constructionPlanes
                plane_input = planes.createInput()
                offset_value = adsk.core.ValueInput.createByReal(z_offset)
                plane_input.setByOffset(selected_plane, offset_value)
                offset_plane = planes.add(plane_input)
                sketch_plane = offset_plane
            else:
                sketch_plane = selected_plane
            # 選択された平面（またはオフセット平面）でスケッチを作成
            sketches = component.sketches

            sketch = sketches.add(sketch_plane)
            # スケッチ作成直後に既存ジオメトリを全削除（ただし原点は残す）
            for curve in list(sketch.sketchCurves.sketchLines):
                curve.deleteMe()
            for curve in list(sketch.sketchCurves.sketchArcs):
                curve.deleteMe()
            for curve in list(sketch.sketchCurves.sketchCircles):
                curve.deleteMe()
            for curve in list(sketch.sketchCurves.sketchEllipses):
                curve.deleteMe()
            for curve in list(sketch.sketchCurves.sketchFittedSplines):
                curve.deleteMe()
            for curve in list(sketch.sketchCurves.sketchFixedSplines):
                curve.deleteMe()
            # スケッチ点（原点）は残す
            
            # 角パイプの断面を描画（中空の四角形）
            lines = sketch.sketchCurves.sketchLines
            thickness = pipe['thickness_mm'] / 10  # mm→cm
            
            # 原点を設定（選択された原点または0,0,0）
            x_offset_input = inputs.itemById('xOffset')
            y_offset_input = inputs.itemById('yOffset')
            rotate_input = inputs.itemById('rotateAngle')
            x_offset = x_offset_input.value if x_offset_input else 0.0
            y_offset = y_offset_input.value if y_offset_input else 0.0
            rotate_angle = rotate_input.value if rotate_input else 0.0  # ラジアン
            if origin_point:
                # 選択された点をスケッチ座標系に変換
                sketch_origin = sketch.modelToSketchSpace(origin_point)
                base_x = sketch_origin.x + x_offset
                base_y = sketch_origin.y + y_offset
            else:
                base_x = x_offset
                base_y = y_offset
            # 回転行列（原点中心、base_x,base_yは回転しない）
            import math
            cos_a = math.cos(rotate_angle)
            sin_a = math.sin(rotate_angle)
            def rot(x, y):
                return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)
            # 外側の四角形
            corners = [
                (0, 0),
                (width, 0),
                (width, height),
                (0, height)
            ]
            rot_corners = [rot(x, y) for x, y in corners]
            points = [adsk.core.Point3D.create(base_x + x, base_y + y, 0) for x, y in rot_corners]
            for i in range(4):
                lines.addByTwoPoints(points[i], points[(i+1)%4])
            # 内側の四角形（中空部分）
            inner_width = width - 2 * thickness
            inner_height = height - 2 * thickness
            if inner_width > 0 and inner_height > 0:
                inner_corners = [
                    (thickness, thickness),
                    (width - thickness, thickness),
                    (width - thickness, height - thickness),
                    (thickness, height - thickness)
                ]
                rot_inner = [rot(x, y) for x, y in inner_corners]
                ipoints = [adsk.core.Point3D.create(base_x + x, base_y + y, 0) for x, y in rot_inner]
                for i in range(4):
                    lines.addByTwoPoints(ipoints[i], ipoints[(i+1)%4])
            
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
                reverse_input = inputs.itemById('reverseDirection')
                reverse = reverse_input.value if reverse_input else False
                # 長さが負の場合は自動的に反転
                extrude_length = abs(length)
                is_negative = (length < 0)
                reverse_final = reverse ^ is_negative  # どちらか一方がTrueなら反転
                distance = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(extrude_length))
                direction_enum = adsk.fusion.ExtentDirections.NegativeExtentDirection if reverse_final else adsk.fusion.ExtentDirections.PositiveExtentDirection
                ext_input.setOneSideExtent(distance, direction_enum)
                extrude = extrudes.add(ext_input)
            
            # タイムライングループ終了
            group_end = timeline.markerPosition
            if group_end > group_start + 1:
                timelineGroups = timeline.timelineGroups
                timelineGroups.add(group_start, group_end - 1)
            
            # プレビュー時はメッセージを出さない
            if hasattr(args, 'isExecute') and args.isExecute:
                ui.messageBox(f'{pipe["width_mm"]}mm x {pipe["height_mm"]}mm t{pipe["thickness_mm"]} 長さ{length*10:.0f}mm のアルミ角パイプを作成しました。')
        
        except:
            if ui:
                ui.messageBox(f'実行失敗:\n{traceback.format_exc()}')
