import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/main.dart';

void main() {
  testWidgets('ECU app renders the main screen', (WidgetTester tester) async {
    await tester.pumpWidget(const EcuAiApp());

    expect(find.text('ECU Calibration Analyzer'), findsWidgets);
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
    expect(find.text('Input'), findsOneWidget);
    expect(find.text('Results'), findsOneWidget);
    expect(find.text('Output'), findsOneWidget);
  });
}
