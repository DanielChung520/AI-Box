/**
 * Icon 渲染器組件
 * 功能：根據圖標名稱動態渲染對應的 react-icons 圖標
 * 支持從 https://react-icons.github.io/react-icons/ 獲取的任意圖標
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2025-01-27
 */

import * as FaIcons from 'react-icons/fa';
import * as Fa6Icons from 'react-icons/fa6';
import * as MdIcons from 'react-icons/md';
import * as HiIcons from 'react-icons/hi';
import * as SiIcons from 'react-icons/si';
import * as Hi2Icons from 'react-icons/hi2';
import * as LuIcons from 'react-icons/lu';
import * as TbIcons from 'react-icons/tb';
import * as RiIcons from 'react-icons/ri';
import * as IoIcons from 'react-icons/io5';

interface IconRendererProps {
  iconName: string;
  size?: number;
  className?: string;
}

// 預定義的 Icon 映射表（常用圖標）
const iconMap: Record<string, any> = {
  // FontAwesome Icons (FA)
  FaRobot: FaIcons.FaRobot,
  FaCode: FaIcons.FaCode,
  FaChartLine: FaIcons.FaChartLine,
  FaBolt: FaIcons.FaBolt,
  FaStar: FaIcons.FaStar,
  FaFire: FaIcons.FaFire,
  FaGem: FaIcons.FaGem,
  FaCrown: FaIcons.FaCrown,
  FaHeart: FaIcons.FaHeart,
  FaRocket: FaIcons.FaRocket,
  FaFileAlt: FaIcons.FaFileAlt,
  FaDatabase: FaIcons.FaDatabase,
  FaCloud: FaIcons.FaCloud,
  FaBriefcase: FaIcons.FaBriefcase,
  FaCodeBranch: FaIcons.FaCodeBranch,
  FaShieldAlt: FaIcons.FaShieldAlt,
  FaCog: FaIcons.FaCog,
  FaLock: FaIcons.FaLock,
  FaKey: FaIcons.FaKey,
  FaSearch: FaIcons.FaSearch,
  FaTools: FaIcons.FaTools,
  FaFingerprint: FaIcons.FaFingerprint,
  FaMagic: FaIcons.FaMagic,
  FaFlask: FaIcons.FaFlask,
  FaBrain: FaIcons.FaBrain,
  FaBuilding: FaIcons.FaBuilding,
  FaChartBar: FaIcons.FaChartBar,
  FaUsers: FaIcons.FaUsers,
  FaGlobe: FaIcons.FaGlobe,
  FaServer: FaIcons.FaServer,
  FaNetworkWired: FaIcons.FaNetworkWired,
  FaMicrochip: FaIcons.FaMicrochip,
  FaLaptopCode: FaIcons.FaLaptopCode,
  FaEye: FaIcons.FaEye,
  FaUserSecret: FaIcons.FaUserSecret,
  FaShieldVirus: FaIcons.FaShieldVirus,
  FaFilter: FaIcons.FaFilter,
  FaWrench: FaIcons.FaWrench,
  FaClipboard: FaIcons.FaClipboard,
  FaBook: FaIcons.FaBook,

  // Material Design Icons (MD)
  MdWork: MdIcons.MdWork,
  MdSchool: MdIcons.MdSchool,
  MdHome: MdIcons.MdHome,
  MdSettings: MdIcons.MdSettings,
  MdNotifications: MdIcons.MdNotifications,
  MdAccountCircle: MdIcons.MdAccountCircle,
  MdBusiness: MdIcons.MdBusiness,

  // Heroicons (HI)
  HiLightBulb: HiIcons.HiLightBulb,
  HiSparkles: HiIcons.HiSparkles,
  HiPuzzle: HiIcons.HiPuzzle,

  // Simple Icons (SI)
  SiPython: SiIcons.SiPython,
  SiJavascript: SiIcons.SiJavascript,
  SiTypescript: SiIcons.SiTypescript,
  SiGo: SiIcons.SiGo,
  SiRust: SiIcons.SiRust,
};

/**
 * 動態獲取圖標組件
 * 根據圖標名稱前綴自動從對應的 react-icons 庫中加載
 * 支持從 https://react-icons.github.io/react-icons/ 獲取的任意圖標
 */
function getDynamicIcon(iconName: string): any {
  // 根據圖標名稱前綴判斷來自哪個庫
  const prefix = iconName.substring(0, 2);
  const fullPrefix = iconName.substring(0, 3);

  try {
    // FontAwesome 5 (Fa)
    if (prefix === 'Fa' && iconName.length > 2 && !iconName.startsWith('Fa6')) {
      return (FaIcons as any)[iconName];
    }
    // FontAwesome 6 (Fa6)
    if (fullPrefix === 'Fa6' && iconName.length > 3) {
      return (Fa6Icons as any)[iconName];
    }
    // Material Design (Md)
    if (prefix === 'Md' && iconName.length > 2) {
      return (MdIcons as any)[iconName];
    }
    // Heroicons (Hi)
    if (prefix === 'Hi' && iconName.length > 2) {
      // Heroicons 1 (Hi)
      const hiIcon = (HiIcons as any)[iconName];
      if (hiIcon) return hiIcon;

      // Heroicons 2 - 處理 HiOutline 和 HiSolid 前綴
      if (iconName.startsWith('HiOutline')) {
        return (Hi2Icons as any)[iconName];
      }
      if (iconName.startsWith('HiSolid')) {
        return (Hi2Icons as any)[iconName];
      }

      // Heroicons 2 - 嘗試直接查找
      return (Hi2Icons as any)[iconName];
    }
    // Simple Icons (Si)
    if (prefix === 'Si' && iconName.length > 2) {
      return (SiIcons as any)[iconName];
    }
    // Lucide (Lu)
    if (prefix === 'Lu' && iconName.length > 2) {
      return (LuIcons as any)[iconName];
    }
    // Tabler Icons (Tb)
    if (prefix === 'Tb' && iconName.length > 2) {
      return (TbIcons as any)[iconName];
    }
    // Remix Icon (Ri)
    if (prefix === 'Ri' && iconName.length > 2) {
      return (RiIcons as any)[iconName];
    }
    // Ionicons 5 (Io)
    if (prefix === 'Io' && iconName.length > 2) {
      return (IoIcons as any)[iconName];
    }

    return null;
  } catch (error) {
    return null;
  }
}

export default function IconRenderer({ iconName, size = 20, className = '' }: IconRendererProps) {
  // 首先從預定義映射表中查找
  let IconComponent = iconMap[iconName];

  // 如果預定義映射表中沒有，嘗試動態加載
  if (!IconComponent) {
    IconComponent = getDynamicIcon(iconName);
  }

  // 如果還是找不到，返回默認圖標
  if (!IconComponent) {
    const DefaultIcon = FaIcons.FaRobot;
    return <DefaultIcon size={size} className={className} />;
  }

  return <IconComponent size={size} className={className} />;
}
