// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart';

void main() {
  testWidgets('ECU app renders the main screen', (WidgetTester tester) async {
    await tester.pumpWidget(const EcuAiApp());

    expect(find.text('ECU Stage 1 Assistant'), findsWidgets);
    expect(find.text('Calibration Input'), findsOneWidget);
    expect(find.text('Analyze calibration'), findsOneWidget);
  });

  testWidgets('ECU app renders the mobile navigation', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const EcuAiApp());

    expect(find.text('ECU AI'), findsOneWidget);
    expect(find.text('Date'), findsOneWidget);
    expect(find.text('Rezultat'), findsOneWidget);
    expect(find.text('Output'), findsOneWidget);
  });
}
