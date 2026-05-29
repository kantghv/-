import 'package:flutter_test/flutter_test.dart';

import 'package:yingxiao_ai_mobile/main.dart';

void main() {
  testWidgets('YingXiao mobile shell starts', (WidgetTester tester) async {
    await tester.pumpWidget(const YingXiaoMobileApp());

    expect(find.text('映效AI'), findsWidgets);
    expect(find.text('移动工作台'), findsOneWidget);
  });
}
